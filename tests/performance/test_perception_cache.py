import asyncio

from app.core.config import settings
from app.models.schemas import ExtractedElement
from app.perception.engine import perception_engine


class FakeBrowser:
    def __init__(self) -> None:
        self.dom_calls = 0

    async def extract_dom_payload(self) -> dict:
        self.dom_calls += 1
        return {
            "title": "Registration",
            "url": "http://localhost:3000/registration",
            "text": "Account Registration",
            "elements": [
                {
                    "id": "email_input",
                    "role": "textbox",
                    "label": "Email",
                    "type": "email",
                    "tag": "input",
                    "name": "email",
                    "value": "",
                    "placeholder": "",
                    "text": "",
                    "visible": True,
                    "enabled": True,
                }
            ],
            "canvases": [],
            "scroll": {"x": 0, "y": 0},
        }

    async def extract_a11y_snapshot(self) -> dict:
        return {"role": "WebArea", "name": "Registration", "children": []}

    async def screenshot(self) -> bytes:
        return b"unused"


def test_perception_cache_reuse_flag_exists():
    assert settings.perception_cache is True
    perception_engine.reset()
    assert perception_engine._cache == {}


def test_perception_cache_hit_on_unchanged_dom(monkeypatch):
    monkeypatch.setattr(settings, "enable_ocr", False)
    monkeypatch.setattr(settings, "perception_cache", True)
    perception_engine.reset()

    async def go():
        browser = FakeBrowser()
        first = await perception_engine.perceive(browser, "register")
        second = await perception_engine.perceive(browser, "register")
        assert first.from_cache is False
        assert second.from_cache is True
        assert isinstance(first.elements[0], ExtractedElement)

    asyncio.run(go())
