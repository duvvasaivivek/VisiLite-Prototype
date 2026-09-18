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


def test_ocr_model_not_preloaded_in_unit_tests():
    assert reader_load_count() in {0, 1}
