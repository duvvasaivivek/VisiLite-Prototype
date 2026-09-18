from app.agent.guard import ActionGuard
from app.models.schemas import ExtractedElement, PerceivedPage, Sensitivity
from app.privacy.vault import vault


def test_local_token_resolution_before_browser():
    vault.reset()
    token = vault.tokenize("John Doe", "PERSON", Sensitivity.PERSONAL)
    page = PerceivedPage(
        page_title="Registration",
        url="http://localhost:3000/registration",
        elements=[
            ExtractedElement(id="name_input", role="textbox", label="Full Name", type="text", visible=True, enabled=True)
        ],
    )
    guard = ActionGuard()
    decision = guard.validate(
        {"action": "fill", "element_id": "name_input", "value": token, "reason": "fill name"},
        page,
        page.url,
    )
    assert decision.approved or decision.confirmation_required
    assert decision.action is not None
    resolved = guard.resolve_tokens(decision.action)
    assert resolved.value == "John Doe"
    assert decision.action.value == token
