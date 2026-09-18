from __future__ import annotations

import hashlib
import io
import time
from typing import Optional

from app.core.config import settings
from app.core.metrics import metrics, timed

_READER = None
_READER_LOAD_COUNT = 0
_OCR_CACHE: dict[str, list[str]] = {}
OCR_EVENTS: list[dict] = []


def reader_load_count() -> int:
    return _READER_LOAD_COUNT


def get_reader():
    global _READER, _READER_LOAD_COUNT
    if not settings.enable_ocr:
        return None
    if _READER is False:
        return None
    if _READER is not None:
        return _READER
    try:
        import easyocr

        _READER = easyocr.Reader(["en"], gpu=False)
        _READER_LOAD_COUNT += 1
        return _READER
    except Exception:
        _READER = False
        return None


def crop_region(image_bytes: bytes, region: dict) -> bytes:
    from PIL import Image

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    x = max(int(region.get("x", 0)), 0)
    y = max(int(region.get("y", 0)), 0)
    w = int(region.get("w") or region.get("width") or 200)
    h = int(region.get("h") or region.get("height") or 80)
    cropped = image.crop((x, y, x + w, y + h))
    out = io.BytesIO()
    cropped.save(out, format="PNG")
    return out.getvalue()


def run_ocr(image_bytes: bytes, reason: str, region: dict | None = None) -> list[str]:
    if not settings.enable_ocr:
        metrics.add(ocr_skipped=1)
        return []
    payload = image_bytes
    dims = "full"
    if region:
        payload = crop_region(image_bytes, region)
        dims = f"{region}"
    key = hashlib.sha256(payload).hexdigest()
    if settings.ocr_cache and key in _OCR_CACHE:
        metrics.add(ocr_skipped=1)
        return _OCR_CACHE[key]
    reader = get_reader()
    if reader is None:
        metrics.add(ocr_skipped=1)
        return []
    with timed() as t:
        result = reader.readtext(payload)
    texts = [item[1] for item in result]
    if settings.ocr_cache:
        _OCR_CACHE[key] = texts
    metrics.add(ocr_invocations=1, ocr_latency_ms_total=t.ms, ocr_regions=1)
    metrics.set(last_ocr_latency_ms=t.ms, last_ocr_reason=reason)
    OCR_EVENTS.append(
        {
            "timestamp": time.time(),
            "reason": reason,
            "region": region or {},
            "image_dimensions": dims,
            "processing_time_ms": round(t.ms, 2),
            "result_count": len(texts),
        }
    )
    return texts


def should_run_ocr(dom_sufficient: bool, canvases: list, required_missing: bool) -> tuple[bool, str]:
    if not settings.enable_ocr:
        return False, "ocr_disabled"
    if dom_sufficient and not required_missing:
        metrics.add(ocr_skipped=1)
        return False, "dom_sufficient"
    if canvases:
        return True, "Canvas contains text not available in DOM"
    if required_missing:
        return True, "Required information missing from DOM/accessibility tree"
    metrics.add(ocr_skipped=1)
    return False, "no_visual_fallback_needed"
