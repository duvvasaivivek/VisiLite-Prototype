from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from time import perf_counter


@dataclass
class PerformanceMetrics:
    dom_scans: int = 0
    dom_latency_ms_total: float = 0.0
    a11y_latency_ms_total: float = 0.0
    ocr_invocations: int = 0
    ocr_skipped: int = 0
    ocr_latency_ms_total: float = 0.0
    last_ocr_latency_ms: float = 0.0
    ocr_regions: int = 0
    last_ocr_reason: str = ""
    llm_calls: int = 0
    llm_latency_ms_total: float = 0.0
    agent_steps: int = 0
    blocked_actions: int = 0
    completed_actions: int = 0
    perception_cache_hits: int = 0
    pii_detected: int = 0
    pii_tokenized: int = 0
    raw_pii_sent_to_ai: int = 0
    sanitized_context_sent: int = 0

    def snapshot(self) -> dict:
        avg_ocr = self.ocr_latency_ms_total / self.ocr_invocations if self.ocr_invocations else 0
        avg_dom = self.dom_latency_ms_total / self.dom_scans if self.dom_scans else 0
        avg_llm = self.llm_latency_ms_total / self.llm_calls if self.llm_calls else 0
        return {
            "dom_scans": self.dom_scans,
            "dom_processing_latency_ms": round(avg_dom, 2),
            "accessibility_processing_latency_ms": round(
                self.a11y_latency_ms_total / self.dom_scans if self.dom_scans else 0, 2
            ),
            "ocr_invocations": self.ocr_invocations,
            "ocr_skipped": self.ocr_skipped,
            "average_ocr_latency_ms": round(avg_ocr, 2),
            "last_ocr_latency_ms": round(self.last_ocr_latency_ms, 2),
            "ocr_regions": self.ocr_regions,
            "last_ocr_reason": self.last_ocr_reason,
            "llm_calls": self.llm_calls,
            "llm_latency_ms": round(avg_llm, 2),
            "agent_steps": self.agent_steps,
            "blocked_actions": self.blocked_actions,
            "completed_actions": self.completed_actions,
            "perception_cache_hits": self.perception_cache_hits,
            "pii_detected": self.pii_detected,
            "pii_tokenized": self.pii_tokenized,
            "raw_pii_sent_to_ai": self.raw_pii_sent_to_ai,
            "sanitized_context_sent": self.sanitized_context_sent,
        }


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self.metrics = PerformanceMetrics()

    def reset(self) -> None:
        with self._lock:
            self.metrics = PerformanceMetrics()

    def add(self, **kwargs) -> None:
        with self._lock:
            for key, value in kwargs.items():
                current = getattr(self.metrics, key)
                setattr(self.metrics, key, current + value)

    def set(self, **kwargs) -> None:
        with self._lock:
            for key, value in kwargs.items():
                setattr(self.metrics, key, value)

    def snapshot(self) -> dict:
        with self._lock:
            return self.metrics.snapshot()


metrics = MetricsRegistry()


class timed:
    def __init__(self) -> None:
        self.ms = 0.0

    def __enter__(self):
        self._start = perf_counter()
        return self

    def __exit__(self, *args):
        self.ms = (perf_counter() - self._start) * 1000
