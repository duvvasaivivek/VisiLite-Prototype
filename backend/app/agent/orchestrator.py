from __future__ import annotations

import asyncio
import uuid
from typing import Optional

from app.agent.guard import action_guard
from app.agent.llm import LLMUnavailable, plan_action
from app.audit.log import audit
from app.browser.adapter import browser_adapter
from app.core.config import settings
from app.core.metrics import metrics
from app.models.schemas import StructuredAction, TaskStatus
from app.perception.engine import perception_engine
from app.privacy.profile import load_profile, tokenize_profile
from app.privacy.sanitizer import PrivacyGatewayError, build_sanitized_context
from app.privacy.vault import vault
from app.security.domains import assert_allowed


class TaskOrchestrator:
    def __init__(self) -> None:
        self.tasks: dict[str, TaskStatus] = {}
        self._pending_action: dict[str, StructuredAction] = {}
        self._last_action_key: dict[str, str] = {}
        self._retries: dict[str, int] = {}
        self.naive_perception = False

    async def create_task(self, instruction: str, start_url: Optional[str] = None) -> TaskStatus:
        metrics.reset()
        vault.reset()
        audit.reset()
        perception_engine.reset()
        task_id = str(uuid.uuid4())[:8]
        status = TaskStatus(id=task_id, instruction=instruction, status="running", message="TASK_STARTED")
        self.tasks[task_id] = status
        self._retries[task_id] = 0
        audit.emit("TASK_STARTED", task_id=task_id, instruction=instruction)
        asyncio.create_task(self._run(task_id, start_url))
        return status

    def get(self, task_id: str) -> TaskStatus:
        return self.tasks[task_id]

    async def approve(self, task_id: str, allow: bool) -> TaskStatus:
        status = self.tasks[task_id]
        if not allow:
            status.status = "blocked"
            status.message = "ACTION BLOCKED by user"
            metrics.add(blocked_actions=1)
            audit.emit("ACTION_BLOCKED", reason="user_denied")
            return status
        action = self._pending_action.get(task_id)
        if not action:
            status.message = "No pending confirmation"
            return status
        status.status = "running"
        status.pending_confirmation = None
        await self._execute(task_id, action, already_validated=True)
        if status.status == "running":
            asyncio.create_task(self._run(task_id, None, continue_existing=True))
        return status

    async def cancel(self, task_id: str) -> TaskStatus:
        status = self.tasks[task_id]
        status.status = "cancelled"
        status.message = "Cancelled"
        return status

    def _default_url(self, instruction: str, start_url: Optional[str]) -> str:
        if start_url:
            return start_url
        text = instruction.lower()
        port = settings.test_sites_port
        if "attack" in text:
            return f"http://localhost:{port}/attack"
        if "travel" in text:
            return f"http://localhost:{port}/travel"
        if "shop" in text or "payment" in text:
            return f"http://localhost:{port}/shopping"
        if "bank" in text:
            return f"http://localhost:{port}/banking"
        if "visual" in text or "coupon" in text or "ocr" in text:
            return f"http://localhost:{port}/visual"
        return f"http://localhost:{port}/registration"

    async def _run(self, task_id: str, start_url: Optional[str], continue_existing: bool = False) -> None:
        status = self.tasks[task_id]
        try:
            if not browser_adapter.ready:
                await browser_adapter.start()
            if not continue_existing:
                url = self._default_url(status.instruction, start_url)
                allowed, reason = assert_allowed(url)
                if not allowed:
                    status.status = "blocked"
                    status.message = reason
                    audit.emit("UNAUTHORIZED_DOMAIN", reason=reason)
                    return
                await browser_adapter.navigate(url)
                audit.emit("PAGE_OBSERVED", url=url)

            profile = load_profile()
            profile_tokens = tokenize_profile(profile)

            while status.status == "running" and status.step < settings.max_agent_steps:
                status.step += 1
                metrics.add(agent_steps=1)
                page = await perception_engine.perceive(
                    browser_adapter, task=status.instruction, naive=self.naive_perception
                )
                audit.emit("DOM_EXTRACTED", url=page.url, cached=page.from_cache)
                if page.ocr_used:
                    audit.emit("OCR_TRIGGERED", reason=page.ocr_reason)
                try:
                    context = build_sanitized_context(page, status.instruction, profile_tokens)
                except PrivacyGatewayError as exc:
                    status.status = "failed"
                    status.message = f"Privacy gateway failed; stopping: {exc}"
                    audit.emit("PRIVACY_GATEWAY_FAILED", error=str(exc))
                    return
                audit.emit("PII_DETECTED", count=metrics.snapshot()["pii_detected"])
                audit.emit("VALUES_TOKENIZED", count=metrics.snapshot()["pii_tokenized"])
                audit.emit("SANITIZED_CONTEXT_CREATED")
                status.last_model_context = context.model_dump()
                status.current_url = page.url
                status.current_page = page.page_title
                await browser_adapter.screenshot()

                extra = ""
                last_key = self._last_action_key.get(task_id)
                if last_key:
                    extra = f"Previous action {last_key} may have failed; replan, do not blindly repeat."

                try:
                    action = plan_action(context, extra)
                    provider = settings.llm_provider.lower()
                    audit.emit("MODEL_CALLED" if provider != "local" else "DETERMINISTIC_ACTION")
                    audit.emit("ACTION_RECEIVED", action=action.action.value, element=action.element_id)
                except LLMUnavailable:
                    status.status = "failed"
                    status.message = "AI reasoning unavailable"
                    return
                except ValueError as exc:
                    status.status = "failed"
                    status.message = str(exc)
                    return

                raw = action.model_dump()
                decision = action_guard.validate(raw, page, page.url)
                status.last_action = raw
                status.last_guard = decision.model_dump()
                audit.emit("ACTION_VALIDATED", approved=decision.approved, blocked=decision.blocked)

                if decision.blocked:
                    status.status = "blocked"
                    status.message = f"ACTION BLOCKED: {decision.reason}"
                    audit.emit("ACTION_BLOCKED", reason=decision.reason)
                    return
                if decision.confirmation_required:
                    self._pending_action[task_id] = action
                    status.status = "awaiting_confirmation"
                    status.pending_confirmation = {
                        "action": action.action.value,
                        "element_id": action.element_id,
                        "value": action.value,
                        "destination": page.url,
                        "reason": decision.reason,
                    }
                    status.message = "CONFIRMATION REQUIRED"
                    return
                if action.action.value == "finish":
                    status.status = "completed"
                    status.message = action.reason or "TASK_COMPLETED"
                    audit.emit("TASK_COMPLETED")
                    return

                await self._execute(task_id, action)
                if status.status != "running":
                    return
            if status.status == "running":
                status.status = "failed"
                status.message = "Stopped safely after MAX_AGENT_STEPS"
        except PermissionError as exc:
            status.status = "blocked"
            status.message = str(exc)
        except Exception as exc:
            status.status = "failed"
            status.message = f"ACTION FAILED: {exc}"
            audit.emit("ACTION_FAILED", error=str(exc))

    async def _execute(self, task_id: str, action: StructuredAction, already_validated: bool = False) -> None:
        status = self.tasks[task_id]
        resolved = action_guard.resolve_tokens(action)
        audit.emit("TOKEN_RESOLVED_LOCALLY", token=action.value if action.value and action.value.startswith("<") else None)
        key = f"{action.action}:{action.element_id}:{action.value}"
        try:
            if action.action.value == "navigate":
                await browser_adapter.navigate(action.url or "")
            elif action.action.value == "click":
                await browser_adapter.click(action.element_id or "")
            elif action.action.value == "fill":
                await browser_adapter.fill(action.element_id or "", resolved.value or "")
            elif action.action.value == "select":
                await browser_adapter.select(action.element_id or "", resolved.value or "")
            elif action.action.value == "scroll":
                await browser_adapter.scroll(action.value or "down")
            elif action.action.value == "wait":
                await browser_adapter.wait(int(action.value or 400))
            elif action.action.value == "extract":
                pass
            metrics.add(completed_actions=1)
            audit.emit("ACTION_EXECUTED", action=action.action.value, element=action.element_id)
            status.current_action = action.action.value
            status.message = action.reason
            self._last_action_key[task_id] = key
            self._retries[task_id] = 0
            await browser_adapter.wait(250)
            audit.emit("PAGE_UPDATED", url=browser_adapter.page.url)
        except Exception as exc:
            self._retries[task_id] = self._retries.get(task_id, 0) + 1
            audit.emit("ACTION_FAILED", error=str(exc), attempt=self._retries[task_id])
            if self._retries[task_id] >= settings.max_action_retries:
                status.status = "failed"
                status.message = f"Retry limit reached: {exc}"
            else:
                status.message = f"ACTION FAILED, replanning ({self._retries[task_id]})"
                self._last_action_key[task_id] = key + ":failed"


orchestrator = TaskOrchestrator()
