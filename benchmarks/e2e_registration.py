"""End-to-end registration benchmark. Starts local test sites and Playwright."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "test-sites"))
os.environ.setdefault("HEADLESS_BROWSER", "true")

from app.core.config import settings  # noqa: E402

settings.headless_browser = True


def _sites():
    import uvicorn
    from server import app as sites_app

    uvicorn.run(sites_app, host="127.0.0.1", port=settings.test_sites_port, log_level="warning")


async def main():
    threading.Thread(target=_sites, daemon=True).start()
    await asyncio.sleep(1.2)

    from app.agent.orchestrator import orchestrator
    from app.browser.adapter import browser_adapter
    from app.core.metrics import metrics
    from app.privacy.vault import vault

    await browser_adapter.start()
    start = time.perf_counter()
    task = await orchestrator.create_task("Fill the registration form using my saved details.")
    status = orchestrator.get(task.id)
    for _ in range(180):
        status = orchestrator.get(task.id)
        if status.status in {"completed", "failed", "blocked", "cancelled"}:
            break
        if status.status == "awaiting_confirmation":
            await orchestrator.approve(task.id, True)
        await asyncio.sleep(0.4)
    elapsed = (time.perf_counter() - start) * 1000
    context = status.last_model_context or {}
    blob = json.dumps(context)
    raw_values = ["john@example.com", "9876543210", "John Doe", "demo-password"]
    leaked = [v for v in raw_values if v in blob]
    result = {
        "status": status.status,
        "message": status.message,
        "steps": status.step,
        "latency_ms": round(elapsed, 2),
        "metrics": metrics.snapshot(),
        "raw_sensitive_values_in_model_context": leaked,
        "vault_tokens": vault.tokens(),
        "last_action": status.last_action,
    }
    out = Path(__file__).resolve().parent / "last_e2e.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    await browser_adapter.close()
    if status.status != "completed" or leaked:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
