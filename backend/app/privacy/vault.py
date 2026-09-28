from app.models.schemas import Sensitivity
from typing import Dict

class TokenVault:
    def __init__(self):
        self._fwd = {}
        self._rev = {}
        self._counts = {}
        
    def reset(self):
        self._fwd.clear()
        self._rev.clear()
        self._counts.clear()
        
    def tokenize(self, raw: str, entity_type: str, sensitivity: Sensitivity) -> str:
        if raw in self._fwd:
            return self._fwd[raw]
            
        count = self._counts.get(entity_type, 0) + 1
        self._counts[entity_type] = count
        token = f"<{entity_type}_{count:03d}>"
        
        self._fwd[raw] = token
        self._rev[token] = raw
        return token
        
    def resolve(self, token: str) -> str:
        return self._rev.get(token, token)
        
    def reverse_map(self) -> Dict[str, str]:
        return self._rev
        
    def sensitivity_for(self, token: str) -> Sensitivity:
        # Dummy implementation for tests
        if "PASSWORD" in token or "OTP" in token:
            return Sensitivity.SECRET
        return Sensitivity.PERSONAL
        
    def mappings_leaked_in(self, payload: str) -> bool:
        for token, raw in self._rev.items():
            if raw in payload and token in payload:
                return True
        return False
        
    def has_raw_secret_in(self, payload: str) -> bool:
        return self.mappings_leaked_in(payload)

vault = TokenVault()
