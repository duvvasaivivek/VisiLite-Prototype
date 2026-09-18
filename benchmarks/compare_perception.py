"""Comparative perception benchmark. Results are generated from real execution."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from app.browser.adapter import BrowserAdapter
from app.core.metrics import metrics
from app.perception.engine import PerceptionEngine
from app.core.config import settings


async def run_mode(naive: bool, url: str, iterations: int = 5) -> dict:
    metrics.reset()
    engine = PerceptionEngine()
    browser = BrowserAdapter()
    await browser.start()
    await browser.navigate(url)
    start = time.perf_counter()
    for _ in range(iterations):
        await engine.perceive(browser, task="read page", force=naive, naive=naive)
    elapsed = (time.perf_counter() - start) * 1000
    await browser.close()
    snap = metrics.snapshot()
    snap["total_latency_ms"] = round(elapsed, 2)
    snap["mode"] = "naive" if naive else "optimized"
    snap["iterations"] = iterations
    return snap


async def main():
    url = f"http://127.0.0.1:{settings.test_sites_port}/registration"
    optimized = await run_mode(False, url)
    naive = await run_mode(True, url)
    result = {"optimized": optimized, "naive": naive}
    out = Path(__file__).resolve().parents[1] / "benchmarks" / "last_run.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
