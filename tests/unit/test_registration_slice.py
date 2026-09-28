from app.security.guard import ActionGuard
from app.agent.llm import plan_action
from app.models.schemas import ExtractedElement, PerceivedPage
from app.privacy.profile import DEFAULT_PROFILE, tokenize_profile
from app.privacy.sanitizer import build_sanitized_context
from app.privacy.vault import vault


def _empty_registration_page() -> PerceivedPage:
    fields = [
        ("name_input", "Full Name", "text"),
        ("email_input", "Email", "email"),
        ("phone_input", "Phone", "tel"),
        ("address_input", "Address", "text"),
        ("dob_input", "Date of Birth", "text"),
        ("city_input", "City", "text"),
    ]
    elements = [
        ExtractedElement(id=eid, role="textbox", label=label, type=itype, tag="input", visible=True, enabled=True)
        for eid, label, itype in fields
    ]
    elements.append(
        ExtractedElement(
            id="submit_registration",
            role="button",
            label="Submit Registration",
            tag="button",
            text="Submit Registration",
            visible=True,
            enabled=True,
        )
    )
    return PerceivedPage(
        page_title="Registration",
        url="http://localhost:3000/registration",
        elements=elements,
    )


def test_registration_sanitized_plan_guard_resolve():
    vault.reset()
    tokens = tokenize_profile(DEFAULT_PROFILE)
    page = _empty_registration_page()
    context = build_sanitized_context(page, "Complete the registration form using my saved details.", tokens)
    blob = context.model_dump_json()
    assert "john@example.com" not in blob
    assert "John Doe" not in blob
    assert "9876543210" not in blob
    assert tokens["Email"].startswith("<")

    action = plan_action(context)
    assert action.action.value == "fill"
    assert action.value and action.value.startswith("<")

    guard = ActionGuard()
    decision = guard.validate(action.model_dump(), page, page.url)
    assert not decision.blocked
    assert decision.approved or decision.confirmation_required
    resolved = guard.resolve_tokens(action)
    assert resolved.value in DEFAULT_PROFILE.values()
    assert action.value != resolved.value or action.value == tokens["City"]
