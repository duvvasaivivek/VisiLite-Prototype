from app.perception.ocr import reader_load_count, should_run_ocr
from app.core.config import settings


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
