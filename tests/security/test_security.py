import pytest

from app.security.domains import assert_allowed
from app.agent.guard import ActionGuard
from app.models.schemas import PerceivedPage, ExtractedElement


def test_navigate_unknown_domain_blocked():
    page = PerceivedPage(page_title="x", url="http://localhost:3000/", elements=[])
    decision = ActionGuard().validate(
        {"action": "navigate", "url": "https://attacker.example", "reason": "exfil"},
        page,
        page.url,
    )
    assert decision.blocked


def test_file_protocol_blocked():
    allowed, reason = assert_allowed("file:///etc/passwd")
    assert not allowed
