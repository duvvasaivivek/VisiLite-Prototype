from __future__ import annotations

from pathlib import Path

from app.models.schemas import Sensitivity
from app.privacy.detector import classify_field
from app.privacy.vault import vault

DEFAULT_PROFILE = {
    "Full Name": "John Doe",
    "Email": "john@example.com",
    "Phone": "9876543210",
    "Address": "12 Demo Street, Hyderabad",
    "Date of Birth": "1999-01-15",
    "City": "Hyderabad",
    "Passenger Name": "John Doe",
    "Source": "Hyderabad",
    "Destination": "Bengaluru",
    "Travel Date": "2026-10-12",
    "Account Number": "123456789012",
    "Beneficiary": "Jane Demo",
    "Amount": "500",
    "Card Number": "4111111111111111",
    "CVV": "123",
    "Transaction Password": "demo-password",
    "OTP": "654321",
}


def load_profile() -> dict[str, str]:
    path = Path(__file__).resolve().parents[2] / "data" / "user_profile.json"
    if path.exists():
        import json

        return json.loads(path.read_text(encoding="utf-8"))
    return dict(DEFAULT_PROFILE)


def tokenize_profile(profile: dict[str, str]) -> dict[str, str]:
    tokens: dict[str, str] = {}
    for label, value in profile.items():
        sensitivity = classify_field(label, "", value)
        if sensitivity == Sensitivity.PUBLIC:
            tokens[label] = value
        else:
            entity = label.upper().replace(" ", "_")
            tokens[label] = vault.tokenize(value, entity, sensitivity)
    return tokens
