from __future__ import annotations

from app.core.metrics import metrics
from app.models.schemas import ExtractedElement, PerceivedPage, SanitizedContext, SanitizedElement, Sensitivity
from app.privacy.detector import classify_field, detect_hybrid
from app.privacy.types import PUBLIC_FIELDS
from app.privacy.vault import vault
from app.security.injection import extract_untrusted_instructions, strip_injection_from_context


def build_sanitized_context(page: PerceivedPage, task: str, user_profile_tokens: dict[str, str]) -> SanitizedContext:
    elements: list[SanitizedElement] = []
    detected = 0
    tokenized = 0
    for el in page.elements:
        findings = detect_hybrid(el.value, el.label or el.name or el.id, el.tag, el.type)
        sensitivity = classify_field(el.label or el.name or el.id, el.type, el.value)
        display_value = el.value
        token = None
        if findings:
            detected += len(findings)
            strongest = max(findings, key=lambda f: list(Sensitivity).index(f.sensitivity))
            sensitivity = strongest.sensitivity
            if el.value and sensitivity != Sensitivity.PUBLIC:
                token = vault.tokenize(el.value, strongest.entity_type, sensitivity)
                display_value = token
                tokenized += 1
        elif el.value and sensitivity in {Sensitivity.PERSONAL, Sensitivity.SENSITIVE, Sensitivity.HIGHLY_SENSITIVE, Sensitivity.SECRET}:
            token = vault.tokenize(el.value, "VALUE", sensitivity)
            display_value = token
            tokenized += 1
            detected += 1
        field_key = (el.label or el.name or "").strip().lower()
        if field_key in PUBLIC_FIELDS and not findings:
            sensitivity = Sensitivity.PUBLIC
            display_value = el.value
        elements.append(
            SanitizedElement(
                id=el.id,
                role=el.role,
                label=el.label or el.text,
                type=el.type,
                tag=el.tag,
                text=el.text,
                value=display_value,
                sensitivity=sensitivity,
                token=token,
            )
        )
    untrusted = extract_untrusted_instructions(page.page_text_sample)
    untrusted.extend(page.untrusted_page_instructions)
    cleaned = [strip_injection_from_context(item) for item in untrusted]
    metrics.add(pii_detected=detected, pii_tokenized=tokenized)
    return SanitizedContext(
        page_title=page.page_title,
        url=page.url,
        task=task,
        elements=elements,
        available_user_tokens=user_profile_tokens,
        webpage_text_untrusted=cleaned[:8],
        ocr_used=page.ocr_used,
    )


def context_contains_raw_protected(context: SanitizedContext, raw_values: list[str]) -> bool:
    blob = context.model_dump_json()
    for value in raw_values:
        if value and value in blob:
            return True
    return False
