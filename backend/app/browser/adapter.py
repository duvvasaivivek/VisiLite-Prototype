from __future__ import annotations

import asyncio
import base64
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from app.core.config import settings
from app.security.domains import assert_allowed


INTERACTIVE_SELECTOR = (
    "input, button, select, textarea, a[href], [role='button'], [role='textbox'], [role='link']"
)


class BrowserAdapter:
    def __init__(self) -> None:
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self.last_screenshot_b64: str = ""
        self.ready = False

    async def start(self) -> None:
        if self._browser:
            return
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=settings.headless_browser,
            slow_mo=settings.playwright_slow_mo,
        )
        self._context = await self._browser.new_context(viewport={"width": 1280, "height": 720})
        self._page = await self._context.new_page()
        self.ready = True

    async def close(self) -> None:
        self.ready = False
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    @property
    def page(self) -> Page:
        if not self._page:
            raise RuntimeError("Browser unavailable")
        return self._page

    async def navigate(self, url: str) -> str:
        allowed, reason = assert_allowed(url)
        if not allowed:
            raise PermissionError(reason)
        await self.page.goto(url, wait_until="domcontentloaded")
        return self.page.url

    async def click(self, element_id: str) -> None:
        locator = self.page.locator(f"#{element_id}")
        await locator.click(timeout=5000)

    async def fill(self, element_id: str, value: str) -> None:
        locator = self.page.locator(f"#{element_id}")
        await locator.fill(value, timeout=5000)

    async def select(self, element_id: str, value: str) -> None:
        locator = self.page.locator(f"#{element_id}")
        await locator.select_option(value)

    async def scroll(self, direction: str = "down") -> None:
        delta = 600 if direction != "up" else -600
        await self.page.mouse.wheel(0, delta)

    async def wait(self, ms: int = 500) -> None:
        await asyncio.sleep(ms / 1000)

    async def screenshot(self) -> bytes:
        data = await self.page.screenshot(type="png")
        self.last_screenshot_b64 = base64.b64encode(data).decode("ascii")
        return data

    async def state(self) -> dict:
        if not self._page:
            return {"ready": False, "url": "", "title": "", "screenshot": ""}
        try:
            await self.screenshot()
        except Exception:
            pass
        return {
            "ready": self.ready,
            "url": self.page.url,
            "title": await self.page.title(),
            "screenshot": self.last_screenshot_b64,
        }

    async def element_meta(self, element_id: str) -> dict:
        locator = self.page.locator(f"#{element_id}")
        count = await locator.count()
        if count == 0:
            return {"exists": False}
        handle = locator.first
        visible = await handle.is_visible()
        enabled = await handle.is_enabled()
        box = await handle.bounding_box()
        return {"exists": True, "visible": visible, "enabled": enabled, "box": box}

    async def extract_dom_payload(self) -> dict:
        return await self.page.evaluate(
            """() => {
              const nodes = Array.from(document.querySelectorAll(
                "input, button, select, textarea, a[href], [role='button'], [role='textbox'], [role='link']"
              ));
              const elements = nodes.map((el, index) => {
                const id = el.id || (`auto_${el.tagName.toLowerCase()}_${index}`);
                if (!el.id) el.id = id;
                const labelEl = el.id ? document.querySelector(`label[for="${el.id}"]`) : null;
                return {
                  id,
                  role: el.getAttribute("role") || el.tagName.toLowerCase(),
                  label: labelEl ? labelEl.innerText.trim() : (el.getAttribute("aria-label") || ""),
                  type: el.getAttribute("type") || "",
                  tag: el.tagName.toLowerCase(),
                  name: el.getAttribute("name") || "",
                  value: el.value || "",
                  placeholder: el.getAttribute("placeholder") || "",
                  text: (el.innerText || el.textContent || "").trim().slice(0, 200),
                  visible: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length),
                  enabled: !el.disabled,
                };
              });
              const canvases = Array.from(document.querySelectorAll("canvas")).map((c, i) => {
                const r = c.getBoundingClientRect();
                return { id: c.id || `canvas_${i}`, x: r.x, y: r.y, w: r.width, h: r.height };
              });
              return {
                title: document.title,
                url: location.href,
                text: document.body ? document.body.innerText.slice(0, 4000) : "",
                elements,
                canvases,
                scroll: { x: window.scrollX, y: window.scrollY },
              };
            }"""
        )

    async def extract_a11y_snapshot(self) -> dict:
        try:
            snapshot = await self.page.accessibility.snapshot()
        except Exception:
            snapshot = None
        return snapshot or {}


browser_adapter = BrowserAdapter()
