from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.models.schemas import Sensitivity


@dataclass
class PIIFinding:
    entity_type: str
    value: str
    start: int
    end: int
    sensitivity: Sensitivity
    detector: str
    field_name: str = ""


FIELD_NAME_MAP: dict[str, tuple[str, Sensitivity]] = {
    "name": ("PERSON", Sensitivity.PERSONAL),
    "full name": ("PERSON", Sensitivity.PERSONAL),
    "passenger": ("PERSON", Sensitivity.PERSONAL),
    "beneficiary": ("PERSON", Sensitivity.PERSONAL),
    "username": ("USERNAME", Sensitivity.SENSITIVE),
    "user name": ("USERNAME", Sensitivity.SENSITIVE),
    "email": ("EMAIL", Sensitivity.PERSONAL),
    "phone": ("PHONE", Sensitivity.SENSITIVE),
    "mobile": ("PHONE", Sensitivity.SENSITIVE),
    "address": ("ADDRESS", Sensitivity.SENSITIVE),
    "shipping address": ("ADDRESS", Sensitivity.SENSITIVE),
    "dob": ("DOB", Sensitivity.SENSITIVE),
    "date of birth": ("DOB", Sensitivity.SENSITIVE),
    "aadhaar": ("AADHAAR", Sensitivity.HIGHLY_SENSITIVE),
    "pan": ("PAN", Sensitivity.HIGHLY_SENSITIVE),
    "account": ("BANK_ACCOUNT", Sensitivity.HIGHLY_SENSITIVE),
    "account number": ("BANK_ACCOUNT", Sensitivity.HIGHLY_SENSITIVE),
    "card": ("CARD", Sensitivity.HIGHLY_SENSITIVE),
    "card number": ("CARD", Sensitivity.HIGHLY_SENSITIVE),
    "cvv": ("CVV", Sensitivity.SECRET),
    "password": ("PASSWORD", Sensitivity.SECRET),
    "transaction password": ("PASSWORD", Sensitivity.SECRET),
    "otp": ("OTP", Sensitivity.SECRET),
    "token": ("AUTH_TOKEN", Sensitivity.SECRET),
    "auth": ("AUTH_TOKEN", Sensitivity.SECRET),
}

PUBLIC_FIELDS = {"city", "source", "destination", "product", "amount", "notes", "coupon"}
