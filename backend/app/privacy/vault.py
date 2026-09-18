from __future__ import annotations

from threading import Lock

from app.models.schemas import Sensitivity


class TokenVault:
    """Local-only mapping from stable tokens to real values."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._token_to_value: dict[str, str] = {}
        self._value_to_token: dict[str, str] = {}
        self._counters: dict[str, int] = {}
        self._token_sensitivity: dict[str, Sensitivity] = {}

    def reset(self) -> None:
        with self._lock:
            self._token_to_value.clear()
            self._value_to_token.clear()
            self._counters.clear()
            self._token_sensitivity.clear()

    def tokenize(self, value: str, entity_type: str, sensitivity: Sensitivity) -> str:
        if not value:
            return value
        with self._lock:
            if value in self._value_to_token:
                return self._value_to_token[value]
            prefix = entity_type.upper().replace(" ", "_")
            self._counters[prefix] = self._counters.get(prefix, 0) + 1
            token = f"<{prefix}_{self._counters[prefix]:03d}>"
            self._token_to_value[token] = value
            self._value_to_token[value] = token
            self._token_sensitivity[token] = sensitivity
            return token

    def resolve(self, maybe_token: str) -> str:
        if not maybe_token:
            return maybe_token
        with self._lock:
            return self._token_to_value.get(maybe_token, maybe_token)

    def contains_token(self, text: str) -> bool:
        with self._lock:
            return any(token in text for token in self._token_to_value)

    def reverse_map(self) -> dict[str, str]:
        with self._lock:
            return dict(self._token_to_value)

    def sensitivity_for(self, token: str) -> Sensitivity | None:
        with self._lock:
            return self._token_sensitivity.get(token)

    def tokens(self) -> list[str]:
        with self._lock:
            return list(self._token_to_value.keys())

    def has_raw_secret_in(self, payload: str) -> bool:
        with self._lock:
            for token, value in self._token_to_value.items():
                sensitivity = self._token_sensitivity.get(token)
                if sensitivity in {Sensitivity.SECRET, Sensitivity.HIGHLY_SENSITIVE, Sensitivity.SENSITIVE, Sensitivity.PERSONAL}:
                    if value and value in payload:
                        return True
            return False

    def mappings_leaked_in(self, payload: str) -> bool:
        with self._lock:
            for token, value in self._token_to_value.items():
                if token in payload and value in payload:
                    return True
            return False


vault = TokenVault()
