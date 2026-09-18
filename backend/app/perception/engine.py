from __future__ import annotations

import hashlib
import json

from app.core.config import settings
from app.core.metrics import metrics, timed
from app.models.schemas import ExtractedElement, PerceivedPage
from app.perception.ocr import run_ocr, should_run_ocr
from app.security.injection import extract_untrusted_instructions


def _fingerprint(url: str, dom_payload: dict, a11y: dict) -> str:
    payload = {
        "url": url,
        "title": dom_payload.get("title"),
        "scroll": dom_payload.get("scroll"),
        "elements": [
            {k: el.get(k) for k in ("id", "value", "text", "label", "type")}
            for el in dom_payload.get("elements", [])
        ],
        "a11y_names": _a11y_names(a11y),
        "canvases": dom_payload.get("canvases"),
    }
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _a11y_names(node: dict, acc: list[str] | None = None) -> list[str]:
    acc = acc or []
    if not node:
        return acc
    name = node.get("name") or ""
    role = node.get("role") or ""
    if name or role:
        acc.append(f"{role}:{name}")
    for child in node.get("children") or []:
        _a11y_names(child, acc)
    return acc[:200]


class PerceptionEngine:
    def __init__(self) -> None:
        self._cache: dict[str, PerceivedPage] = {}

    def reset(self) -> None:
        self._cache.clear()

    async def perceive(self, browser, task: str = "", force: bool = False, naive: bool = False) -> PerceivedPage:
        with timed() as dom_t:
            dom_payload = await browser.extract_dom_payload()
        with timed() as a11y_t:
            a11y = await browser.extract_a11y_snapshot()
        metrics.add(dom_scans=1, dom_latency_ms_total=dom_t.ms, a11y_latency_ms_total=a11y_t.ms)

        url = dom_payload.get("url", "")
        fp = _fingerprint(url, dom_payload, a11y)
        if settings.perception_cache and not force and not naive and fp in self._cache:
            cached = self._cache[fp].model_copy()
            cached.from_cache = True
            metrics.add(perception_cache_hits=1, ocr_skipped=1)
            return cached

        elements = [ExtractedElement(**item) for item in dom_payload.get("elements", [])]
        a11y_names = _a11y_names(a11y)
        for el in elements:
            if not el.label:
                for name in a11y_names:
                    if el.id in name or el.text and el.text in name:
                        el.label = name.split(":", 1)[-1]
                        break

        page_text = dom_payload.get("text") or ""
        canvases = dom_payload.get("canvases") or []
        interactive = [el for el in elements if el.visible]
        required_missing = self._required_missing(task, interactive, page_text)
        dom_sufficient = bool(interactive) and not required_missing and not canvases

        ocr_used = False
        ocr_reason = ""
        if naive:
            screenshot = await browser.screenshot()
            texts = run_ocr(screenshot, "naive_full_frame_ocr", None)
            if texts:
                page_text += "\n" + "\n".join(texts)
            ocr_used = True
            ocr_reason = "naive_full_frame_ocr"
        else:
            run, reason = should_run_ocr(dom_sufficient, canvases, required_missing)
            ocr_reason = reason
            if run:
                screenshot = await browser.screenshot()
                region = canvases[0] if canvases else None
                texts = run_ocr(screenshot, reason, region)
                if texts:
                    page_text += "\n" + "\n".join(texts)
                ocr_used = True
            else:
                metrics.add(ocr_skipped=0)

        page = PerceivedPage(
            page_title=dom_payload.get("title") or "",
            url=url,
            elements=elements,
            page_text_sample=page_text[:4000],
            untrusted_page_instructions=extract_untrusted_instructions(page_text),
            fingerprint=fp,
            ocr_used=ocr_used,
            ocr_reason=ocr_reason,
        )
        if settings.perception_cache:
            self._cache[fp] = page
        return page

    def _required_missing(self, task: str, elements: list[ExtractedElement], page_text: str) -> bool:
        lowered = (task + " " + page_text).lower()
        if "coupon" in lowered and "vlite" not in page_text.lower():
            if not any("coupon" in (el.value or "").lower() for el in elements):
                return True
        return False


perception_engine = PerceptionEngine()
