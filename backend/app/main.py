from contextlib import asynccontextmanager
from pathlib import Path
import sys
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.browser.adapter import browser_adapter
import os

from app.core.config import settings

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "test-sites") not in sys.path:
    sys.path.append(str(ROOT / "test-sites"))


def _start_test_sites():
    import uvicorn
    from server import app as sites_app

    uvicorn.run(sites_app, host="127.0.0.1", port=settings.test_sites_port, log_level="warning")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("VISILITE_SKIP_TEST_SITES") != "1":
        thread = threading.Thread(target=_start_test_sites, daemon=True)
        thread.start()
    if os.getenv("VISILITE_SKIP_BROWSER") != "1":
        try:
            await browser_adapter.start()
        except Exception:
            pass
    yield
    if browser_adapter.ready:
        await browser_adapter.close()


app = FastAPI(title="VisiLite", description="Privacy-Preserving Visual Agent for Secure Web Automation", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")
