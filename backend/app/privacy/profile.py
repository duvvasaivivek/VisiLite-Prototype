from app.privacy.vault import vault
from app.models.schemas import Sensitivity

DEFAULT_PROFILE = {
    "Full Name": "John Doe",
    "Email": "john@example.com",
    "City": "Hyderabad"
}

def tokenize_profile(profile: dict) -> dict:
    tokens = {}
    for k, v in profile.items():
        if k in ("City", "State", "Country"):
            tokens[k] = v
        else:
            token = vault.tokenize(v, k.upper().replace(" ", "_"), Sensitivity.PERSONAL)
            tokens[k] = token
    return tokens
