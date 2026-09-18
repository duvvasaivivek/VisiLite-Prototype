from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings
from app.models.schemas import Sensitivity


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str
    confirmation_required: bool = False
    fail_closed: bool = False


TRANSMISSION_POLICY = {
    Sensitivity.PUBLIC: "may_share",
    Sensitivity.NORMAL: "may_share",
    Sensitivity.PERSONAL: "restricted",
    Sensitivity.SENSITIVE: "protected",
    Sensitivity.HIGHLY_SENSITIVE: "protected",
    Sensitivity.SECRET: "never",
}


class PolicyEngine:
    def may_transmit_externally(self, sensitivity: Sensitivity, destination_allowed: bool) -> PolicyDecision:
        rule = TRANSMISSION_POLICY.get(sensitivity, "protected")
        if rule == "never":
            return PolicyDecision(False, "SECRET values must never leave the trusted privacy boundary.", fail_closed=True)
        if rule == "protected":
            return PolicyDecision(
                False,
                "Protected information cannot leave the trusted privacy boundary.",
                fail_closed=True,
            )
        if rule == "restricted":
            if not destination_allowed:
                return PolicyDecision(False, "PERSONAL data cannot be sent to an unapproved destination.")
            if settings.require_confirmation_for_sensitive_actions:
                return PolicyDecision(True, "PERSONAL data requires confirmation before external use.", confirmation_required=True)
        if not destination_allowed:
            return PolicyDecision(False, "Destination is not on the V1 domain allowlist.")
        return PolicyDecision(True, "Transmission permitted under current policy.")

    def action_risk(self, action: str, sensitivity: Sensitivity | None, url: str | None = None) -> str:
        if action in {"navigate"} and url and not self._local(url):
            return "high"
        if sensitivity in {Sensitivity.SECRET, Sensitivity.HIGHLY_SENSITIVE}:
            return "high"
        if sensitivity == Sensitivity.SENSITIVE:
            return "medium"
        if action in {"click"} and any(word in (url or "").lower() for word in ["pay", "transfer", "submit"]):
            return "medium"
        return "low"

    def requires_confirmation(self, action: str, risk: str, label: str = "") -> bool:
        if not settings.require_confirmation_for_sensitive_actions:
            return False
        lowered = f"{action} {label}".lower()
        if any(word in lowered for word in ["payment", "pay", "transfer", "password", "otp", "card"]):
            return True
        return risk == "high"

    def _local(self, url: str) -> bool:
        return "localhost" in url or "127.0.0.1" in url


policy_engine = PolicyEngine()
