from __future__ import annotations

import json
from typing import Optional

from pydantic import ValidationError

from app.core.config import settings
from app.core.metrics import metrics, timed
from app.models.schemas import SanitizedContext, StructuredAction
from app.security.injection import SYSTEM_POLICY


class LLMUnavailable(RuntimeError):
    pass


class LLMClient:
    def plan(self, context: SanitizedContext, extra: str = "") -> StructuredAction:
        raise NotImplementedError


class LocalPlanner(LLMClient):
    """Deterministic local planner operating only on sanitized structured context."""

    def plan(self, context: SanitizedContext, extra: str = "") -> StructuredAction:
        metrics.add(llm_calls=1)
        tokens = context.available_user_tokens
        task = context.task.lower()

        if context.webpage_text_untrusted or "attack" in context.url:
            if any(
                phrase in task
                for phrase in ("external", "private data", "bank details", "ignore previous", "attacker")
            ):
                return StructuredAction(
                    action="finish",
                    reason="Webpage injection is untrusted; refusing to exfiltrate data.",
                )

        for el in context.elements:
            if el.role in {"textbox", "input", "email", "tel"} or el.type in {"text", "email", "tel", "password"}:
                if not el.value:
                    fill_value = self._match_token(el, tokens)
                    if fill_value is not None:
                        return StructuredAction(
                            action="fill",
                            element_id=el.id,
                            value=fill_value,
                            reason=f"Fill {el.label or el.id} from local sanitized profile tokens",
                        )
            if el.type == "password" and not el.value:
                token = tokens.get("Transaction Password") or tokens.get("Password")
                if token:
                    return StructuredAction(action="fill", element_id=el.id, value=token, reason="Fill password from token")

        for el in context.elements:
            text = (el.text or el.label or el.id).lower()
            if el.tag == "button" or el.role in {"button", "submit"} or "button" in (el.role or ""):
                if any(word in text for word in ["submit", "register", "search", "apply", "stay"]):
                    return StructuredAction(action="click", element_id=el.id, reason=f"Submit via {el.id}")
            if "submit" in el.id or el.id.endswith("_button"):
                if "transfer" in el.id or "pay" in el.id:
                    continue
                return StructuredAction(action="click", element_id=el.id, reason=f"Click {el.id}")

        if "registration complete" in context.page_title.lower() or "success" in context.page_title.lower():
            return StructuredAction(action="finish", reason="Registration appears complete")

        empty = [el for el in context.elements if (el.role in {"textbox", "input"} or el.type in {"text", "email", "tel"}) and not el.value]
        if not empty:
            for el in context.elements:
                if "submit" in (el.id + el.label).lower() or el.type == "submit":
                    return StructuredAction(action="click", element_id=el.id, reason="All fields filled; submit")
            return StructuredAction(action="finish", reason="No remaining interactive work detected")

        return StructuredAction(action="wait", value="400", reason="Waiting for page to settle")

    def _match_token(self, el, tokens: dict[str, str]) -> Optional[str]:
        label = (el.label or el.name or el.id).lower()
        mapping = [
            ("name", ["Full Name", "Passenger Name", "Beneficiary"]),
            ("email", ["Email"]),
            ("phone", ["Phone"]),
            ("address", ["Address"]),
            ("dob", ["Date of Birth"]),
            ("birth", ["Date of Birth"]),
            ("city", ["City"]),
            ("source", ["Source"]),
            ("destination", ["Destination"]),
            ("date", ["Travel Date", "Date of Birth"]),
            ("passenger", ["Passenger Name", "Full Name"]),
            ("product", ["Product"] if False else []),
            ("account", ["Account Number"]),
            ("beneficiary", ["Beneficiary"]),
            ("amount", ["Amount"]),
            ("card", ["Card Number"]),
            ("cvv", ["CVV"]),
            ("otp", ["OTP"]),
            ("password", ["Transaction Password"]),
            ("coupon", []),
            ("notes", []),
        ]
        for needle, keys in mapping:
            if needle in label:
                for key in keys:
                    if key in tokens:
                        return tokens[key]
                if needle == "coupon":
                    return "VLITE-42"
                if needle == "notes":
                    return "local-safe-note"
                if needle == "product":
                    return el.value or "Synthetic Demo Headphones"
        for key, token in tokens.items():
            if key.lower() in label:
                return token
        return None


class GeminiPlanner(LLMClient):
    """Calls the Google Gemini REST API with sanitized context only."""

    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def plan(self, context: SanitizedContext, extra: str = "") -> StructuredAction:
        if not settings.llm_api_key:
            raise LLMUnavailable("AI reasoning unavailable")
        try:
            import httpx
        except Exception as exc:
            raise LLMUnavailable("AI reasoning unavailable") from exc

        user_content = json.dumps(
            {
                "task": context.task,
                "sanitized_page": context.model_dump(),
                "extra": extra,
                "schema": {
                    "action": "navigate|click|fill|select|scroll|wait|extract|finish",
                    "element_id": "string",
                    "value": "token or public value",
                    "url": "optional",
                    "reason": "string",
                },
            }
        )

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{SYSTEM_POLICY}\n\n{user_content}"}],
                }
            ],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
            },
        }

        url = self.GEMINI_API_URL.format(model=settings.llm_model)
        with timed() as t:
            response = httpx.post(
                url,
                json=payload,
                params={"key": settings.llm_api_key},
                headers={"Content-Type": "application/json"},
                timeout=60,
            )
        metrics.add(llm_calls=1, llm_latency_ms_total=t.ms)
        if response.status_code >= 400:
            raise LLMUnavailable("AI reasoning unavailable")
        try:
            resp_json = response.json()
            content = resp_json["candidates"][0]["content"]["parts"][0]["text"]
            data = json.loads(content)
            return StructuredAction.model_validate(data)
        except (json.JSONDecodeError, ValidationError, KeyError, TypeError, IndexError) as exc:
            raise ValueError(f"Malformed model output: {exc}") from exc


def get_planner() -> LLMClient:
    provider = settings.llm_provider.lower()
    if provider == "gemini":
        if settings.llm_api_key:
            return GeminiPlanner()
        return LocalPlanner()
    return LocalPlanner()


def plan_action(context: SanitizedContext, extra: str = "") -> StructuredAction:
    planner = get_planner()
    try:
        action = planner.plan(context, extra)
    except LLMUnavailable:
        raise
    except (ValidationError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError(f"Malformed model output: {exc}") from exc
    metrics.add(sanitized_context_sent=1)
    if vault_has_raw_in_context(context):
        metrics.set(raw_pii_sent_to_ai=metrics.metrics.raw_pii_sent_to_ai + 1)
    return action


def vault_has_raw_in_context(context: SanitizedContext) -> bool:
    from app.privacy.vault import vault

    return vault.has_raw_secret_in(context.model_dump_json())
