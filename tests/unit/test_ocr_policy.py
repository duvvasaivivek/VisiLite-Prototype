from app.perception.ocr import reader_load_count, reset_ocr_state, run_ocr, should_run_ocr
from app.core.config import settings
from app.perception import ocr as ocr_mod


def test_ocr_not_automatic_when_dom_sufficient():
    run, reason = should_run_ocr(dom_sufficient=True, canvases=[], required_missing=False)
    assert run is False
    assert reason == "dom_sufficient"


def test_ocr_runs_for_canvas_fallback():
    if not settings.enable_ocr:
        return
    run, reason = should_run_ocr(dom_sufficient=False, canvases=[{"x": 1, "y": 1, "w": 10, "h": 10}], required_missing=True)
    assert run is True
    assert "Canvas" in reason or "missing" in reason.lower()


def test_visual_ocr_fallback_not_used_when_dom_has_fields():
    run, reason = should_run_ocr(dom_sufficient=True, canvases=[], required_missing=False)
    assert run is False
    assert reason == "dom_sufficient"


def test_ocr_model_not_preloaded_in_unit_tests():
    assert reader_load_count() in {0, 1}


def test_ocr_cache_reuses_identical_image(monkeypatch):
    reset_ocr_state()
    calls = {"n": 0}

    class FakeReader:
        def readtext(self, payload):
            calls["n"] += 1
            return [([0], "VLITE-42", 0.9)]

    monkeypatch.setattr(ocr_mod, "get_reader", lambda: FakeReader())
    monkeypatch.setattr(settings, "enable_ocr", True)
    monkeypatch.setattr(settings, "ocr_cache", True)
    first = run_ocr(b"same-bytes", "visual_fallback", None)
    second = run_ocr(b"same-bytes", "visual_fallback", None)
    third = run_ocr(b"other-bytes", "visual_fallback", None)
    assert first == ["VLITE-42"]
    assert second == ["VLITE-42"]
    assert calls["n"] == 2
    assert third == ["VLITE-42"]

import pytest
from app.perception.engine import PerceptionEngine

@pytest.mark.asyncio
async def test_ocr_fallback_e2e_mock(monkeypatch):
    class MockBrowser:
        async def extract_dom_payload(self):
            return {
                "url": "http://localhost:3000/visual",
                "title": "Visual Only",
                "elements": [],
                "text": "The coupon code is drawn on a canvas and is not present as DOM text.",
                "canvases": [{"x": 10, "y": 10, "w": 100, "h": 50}]
            }
        async def extract_a11y_snapshot(self):
            return {}
        async def screenshot(self):
            return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'

    monkeypatch.setattr(settings, "enable_ocr", True)
    monkeypatch.setattr(settings, "ocr_cache", False)
    
    class FakeReader:
        def readtext(self, payload):
            return [([0], "COUPON VLITE-42", 0.9)]
            
    monkeypatch.setattr(ocr_mod, "get_reader", lambda: FakeReader())

    engine = PerceptionEngine()
    page = await engine.perceive(MockBrowser(), task="find coupon")
    
    assert page.ocr_used is True
    assert "Canvas" in page.ocr_reason or "missing" in page.ocr_reason.lower()
    assert "VLITE-42" in page.page_text_sample
