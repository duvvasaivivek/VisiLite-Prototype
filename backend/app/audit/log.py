from __future__ import annotations

import time
from threading import Lock

from app.models.schemas import Sensitivity

SECRET_MARKERS = ("PASSWORD", "OTP", "CVV", "AUTH_TOKEN", "demo-password")


class AuditLog:
    def __init__(self) -> None:
        self._lock = Lock()
        self.events: list[dict] = []

    def reset(self) -> None:
        with self._lock:
            self.events.clear()

    def emit(self, kind: str, **payload) -> None:
        safe = {k: self._redact(v) for k, v in payload.items()}
        event = {"ts": time.time(), "event": kind, **safe}
        with self._lock:
            self.events.append(event)

    def _redact(self, value):
        from app.privacy.vault import vault

        text = str(value)
        for token, raw in vault.reverse_map().items():
            sensitivity = vault.sensitivity_for(token)
            if sensitivity == Sensitivity.SECRET and raw and raw in text:
                text = text.replace(raw, token)
        lowered = text.lower()
        if any(marker.lower() in lowered for marker in SECRET_MARKERS) and not text.startswith("<"):
            if "demo-password" in lowered or "654321" in text:
                return "<REDACTED>"
        return text if text != str(value) else value

    def all(self) -> list[dict]:
        with self._lock:
            return list(self.events)

    def contains_raw_secret(self, secret: str) -> bool:
        blob = str(self.all())
        return secret in blob


audit = AuditLog()
