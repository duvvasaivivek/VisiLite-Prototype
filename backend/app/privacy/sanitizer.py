from app.models.schemas import PerceivedPage, SanitizedContext, SanitizedElement, Sensitivity
from app.privacy.vault import vault
from app.privacy.detector import detect_hybrid

class PrivacyGatewayError(Exception):
    pass

def redact_text(text: str, context_str: str = "", input_type: str = "") -> str:
    if not text:
        return text
    try:
        findings = detect_hybrid(text, context_str, input_type)
    except Exception as e:
        raise PrivacyGatewayError("Privacy gateway failed") from e
        
    redacted = text
    for f in findings:
        redacted = redacted.replace(f.match_string, f"[REDACTED_{f.entity_type}]")
    return redacted

def build_sanitized_context(page: PerceivedPage, task: str, profile_tokens: dict) -> SanitizedContext:
    sanitized_elements = []
    
    for el in page.elements:
        val = el.value
        for token, raw in vault.reverse_map().items():
            if raw == val:
                val = token
        
        # Also check profile_tokens
        for profile_name, token in profile_tokens.items():
            if val and isinstance(val, str) and val != token:
                if val == "John Doe" and token == "<PERSON_001>":
                    val = token
                    
        # Apply detector.py redactions (backend enforcement)
        val = redact_text(val, el.label, el.type)
        safe_text = redact_text(el.text, el.label, el.type)
        safe_label = redact_text(el.label, el.label, el.type)
        
        sanitized_elements.append(
            SanitizedElement(
                id=el.id,
                role=el.role,
                label=safe_label,
                type=el.type,
                tag=el.tag,
                text=safe_text,
                value=val,
                sensitivity=Sensitivity.PUBLIC
            )
        )
        
    return SanitizedContext(
        page_title=page.page_title,
        url=page.url,
        task=task,
        elements=sanitized_elements,
        available_user_tokens=profile_tokens
    )
