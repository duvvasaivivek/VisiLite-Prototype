from __future__ import annotations

import re
from typing import Optional

from app.models.schemas import Sensitivity
from app.privacy.types import FIELD_NAME_MAP, PIIFinding, PUBLIC_FIELDS

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b")
AADHAAR_RE = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
CARD_RE = re.compile(r"\b(?:\d{4}[\s-]?){3}\d{4}\b")
BANK_RE = re.compile(r"\b\d{9,18}\b")
OTP_RE = re.compile(r"\b\d{4,8}\b")
DOB_RE = re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})\b")


def _add(findings: list[PIIFinding], finding: PIIFinding) -> None:
    if not finding.value or (finding.value.startswith("<") and finding.value.endswith(">")):
        return
    findings.append(finding)


def detect_by_regex(text: str, field_name: str = "") -> list[PIIFinding]:
    findings: list[PIIFinding] = []
    for match in EMAIL_RE.finditer(text):
        _add(findings, PIIFinding("EMAIL", match.group(), match.start(), match.end(), Sensitivity.PERSONAL, "regex", field_name))
    for match in PHONE_RE.finditer(text):
        _add(findings, PIIFinding("PHONE", match.group(), match.start(), match.end(), Sensitivity.SENSITIVE, "regex", field_name))
    for match in PAN_RE.finditer(text):
        _add(findings, PIIFinding("PAN", match.group(), match.start(), match.end(), Sensitivity.HIGHLY_SENSITIVE, "regex", field_name))
    for match in CARD_RE.finditer(text):
        _add(findings, PIIFinding("CARD", match.group(), match.start(), match.end(), Sensitivity.HIGHLY_SENSITIVE, "regex", field_name))
    for match in AADHAAR_RE.finditer(text):
        _add(findings, PIIFinding("AADHAAR", match.group(), match.start(), match.end(), Sensitivity.HIGHLY_SENSITIVE, "regex", field_name))
    for match in DOB_RE.finditer(text):
        _add(findings, PIIFinding("DOB", match.group(), match.start(), match.end(), Sensitivity.SENSITIVE, "regex", field_name))
    return findings


def detect_by_field_name(field_name: str, value: str) -> Optional[PIIFinding]:
    key = field_name.strip().lower()
    if not value:
        return None
    if key in PUBLIC_FIELDS:
        return None
    for name, (entity, sensitivity) in FIELD_NAME_MAP.items():
        if name in key:
            return PIIFinding(entity, value, 0, len(value), sensitivity, "field_name", field_name)
    return None


def detect_semantic(field_name: str, input_type: str, value: str) -> Optional[PIIFinding]:
    t = (input_type or "").lower()
    if t in {"password"}:
        return PIIFinding("PASSWORD", value or "***", 0, len(value or "***"), Sensitivity.SECRET, "semantic", field_name)
    if t in {"email"}:
        return PIIFinding("EMAIL", value, 0, len(value), Sensitivity.PERSONAL, "semantic", field_name) if value else None
    if t in {"tel"}:
        return PIIFinding("PHONE", value, 0, len(value), Sensitivity.SENSITIVE, "semantic", field_name) if value else None
    lowered = field_name.lower()
    if "otp" in lowered:
        return PIIFinding("OTP", value or "", 0, len(value or ""), Sensitivity.SECRET, "semantic", field_name)
    if "cvv" in lowered or "cvc" in lowered:
        return PIIFinding("CVV", value or "", 0, len(value or ""), Sensitivity.SECRET, "semantic", field_name)
    return None


def detect_presidio(text: str) -> list[PIIFinding]:
    from app.core.config import settings

    if not settings.enable_presidio:
        return []
    try:
        from presidio_analyzer import AnalyzerEngine
    except Exception:
        return []
    analyzer = _presidio_singleton()
    if analyzer is None:
        return []
    results = analyzer.analyze(text=text, language="en")
    mapped: list[PIIFinding] = []
    for item in results:
        entity = item.entity_type.upper()
        sensitivity = Sensitivity.PERSONAL
        if entity in {"CREDIT_CARD", "IBAN_CODE", "US_SSN"}:
            sensitivity = Sensitivity.HIGHLY_SENSITIVE
        mapped.append(
            PIIFinding(
                entity_type=entity,
                value=text[item.start : item.end],
                start=item.start,
                end=item.end,
                sensitivity=sensitivity,
                detector="presidio",
            )
        )
    return mapped


_PRESIDIO = None


def _presidio_singleton():
    global _PRESIDIO
    if _PRESIDIO is False:
        return None
    if _PRESIDIO is not None:
        return _PRESIDIO
    try:
        from presidio_analyzer import AnalyzerEngine

        _PRESIDIO = AnalyzerEngine()
        return _PRESIDIO
    except Exception:
        _PRESIDIO = False
        return None


def classify_field(field_name: str, input_type: str = "", value: str = "") -> Sensitivity:
    key = field_name.strip().lower()
    if key in PUBLIC_FIELDS:
        return Sensitivity.PUBLIC
    semantic = detect_semantic(field_name, input_type, value)
    if semantic:
        return semantic.sensitivity
    named = detect_by_field_name(field_name, value or field_name)
    if named:
        return named.sensitivity
    return Sensitivity.NORMAL


def detect_hybrid(text: str = "", field_name: str = "", html_context: str = "", input_type: str = "") -> list[PIIFinding]:
    findings: list[PIIFinding] = []
    if text:
        findings.extend(detect_by_regex(text, field_name))
        findings.extend(detect_presidio(text))
    named = detect_by_field_name(field_name, text)
    if named:
        findings.append(named)
    semantic = detect_semantic(field_name, input_type, text)
    if semantic:
        findings.append(semantic)
    if html_context and "password" in html_context.lower():
        findings.append(PIIFinding("PASSWORD", text or "", 0, len(text or ""), Sensitivity.SECRET, "html_context", field_name))
    unique: dict[tuple[str, str], PIIFinding] = {}
    for item in findings:
        unique[(item.entity_type, item.value)] = item
    return list(unique.values())
