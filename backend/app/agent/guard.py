from __future__ import annotations

from pydantic import ValidationError

from app.core.metrics import metrics
from app.models.schemas import ActionDecision, PerceivedPage, StructuredAction, Sensitivity
from app.privacy.policy import policy_engine
from app.privacy.vault import vault
from app.security.domains import assert_allowed


HIGH_RISK_IDS = {"pay_button", "transfer_button"}


class ActionGuard:
    def validate(self, raw: dict, page: PerceivedPage, current_url: str) -> ActionDecision:
        try:
            action = StructuredAction.model_validate(raw)
        except ValidationError as exc:
            metrics.add(blocked_actions=1)
            return ActionDecision(approved=False, blocked=True, reason=f"Schema validation failed: {exc}")

        if action.action.value not in {item.value for item in type(action.action)}:
            metrics.add(blocked_actions=1)
            return ActionDecision(approved=False, blocked=True, reason="Unsupported action type")

        if action.action.value == "navigate":
            allowed, reason = assert_allowed(action.url or "")
            if not allowed:
                metrics.add(blocked_actions=1)
                return ActionDecision(approved=False, blocked=True, reason=reason, destination=action.url)
            risk = policy_engine.action_risk("navigate", None, action.url)
            confirm = policy_engine.requires_confirmation("navigate", risk, action.url or "")
            return ActionDecision(
                approved=not confirm,
                confirmation_required=confirm,
                reason=reason,
                risk=risk,
                destination=action.url,
                action=action,
            )

        if action.action.value == "finish":
            return ActionDecision(approved=True, reason="Finish requested", action=action)

        if action.action.value in {"click", "fill", "select"}:
            if not action.element_id:
                metrics.add(blocked_actions=1)
                return ActionDecision(approved=False, blocked=True, reason="Missing element_id")
            match = next((el for el in page.elements if el.id == action.element_id), None)
            if not match:
                metrics.add(blocked_actions=1)
                return ActionDecision(approved=False, blocked=True, reason="Invalid element: not found in current DOM")
            if not match.visible:
                metrics.add(blocked_actions=1)
                return ActionDecision(approved=False, blocked=True, reason="Element is not visible")
            if not match.enabled:
                metrics.add(blocked_actions=1)
                return ActionDecision(approved=False, blocked=True, reason="Element is not interactable")

        if action.action.value == "fill" and action.value:
            if self._looks_like_exfil(action, page):
                metrics.add(blocked_actions=1)
                return ActionDecision(
                    approved=False,
                    blocked=True,
                    reason="Protected information cannot leave the trusted privacy boundary.",
                    action=action,
                )
            sensitivity = vault.sensitivity_for(action.value)
            if sensitivity in {Sensitivity.HIGHLY_SENSITIVE, Sensitivity.SECRET} and action.element_id in HIGH_RISK_IDS:
                metrics.add(blocked_actions=1)
                return ActionDecision(
                    approved=False,
                    blocked=True,
                    reason="Protected information cannot leave the trusted privacy boundary.",
                    action=action,
                )
            risk = policy_engine.action_risk("fill", sensitivity, current_url)
            confirm = policy_engine.requires_confirmation("fill", risk, action.element_id or "")
            if action.element_id in HIGH_RISK_IDS:
                confirm = True
                risk = "high"
            return ActionDecision(
                approved=not confirm,
                confirmation_required=confirm,
                reason="Fill validated; token will be resolved locally",
                risk=risk,
                resolved_value_present=action.value.startswith("<") if action.value else False,
                action=action,
            )

        if action.action.value == "click" and action.element_id in HIGH_RISK_IDS:
            return ActionDecision(
                approved=False,
                confirmation_required=True,
                reason="High-risk submission requires confirmation",
                risk="high",
                action=action,
            )

        allowed_page, page_reason = assert_allowed(current_url)
        if not allowed_page:
            metrics.add(blocked_actions=1)
            return ActionDecision(approved=False, blocked=True, reason=page_reason)

        return ActionDecision(approved=True, reason="Action validated", action=action, risk="low")

    def _looks_like_exfil(self, action: StructuredAction, page: PerceivedPage) -> bool:
        if action.url and not assert_allowed(action.url)[0]:
            return True
        if action.element_id and "external" in action.element_id:
            return True
        blob = (action.reason or "").lower()
        if "external server" in blob or "evil" in blob:
            return True
        if any("send the user's" in item.lower() for item in page.untrusted_page_instructions):
            if action.action.value == "navigate":
                return True
        return False

    def resolve_tokens(self, action: StructuredAction) -> StructuredAction:
        resolved = action.model_copy()
        if resolved.value:
            resolved.value = vault.resolve(resolved.value)
        return resolved


action_guard = ActionGuard()
