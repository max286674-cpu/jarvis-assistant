"""Optional Playwright browser adapter; reuses a visible local browser session when configured."""
from __future__ import annotations
import os

class BrowserAgent:
    def __init__(self):
        self._playwright = None
        self._browser = None
        self._page = None

    def _ensure(self):
        if self._page is not None:
            return self._page
        from playwright.sync_api import sync_playwright
        self._playwright = sync_playwright().start()
        browser_path = os.getenv("JARVIS_BROWSER_EXECUTABLE", "")
        if browser_path:
            self._browser = self._playwright.chromium.launch(headless=False, executable_path=browser_path)
        else:
            self._browser = self._playwright.chromium.launch(headless=False)
        context = self._browser.new_context()
        self._page = context.new_page()
        return self._page

    def open(self, url: str):
        page = self._ensure()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return {"title": page.title(), "url": page.url()}

    def snapshot(self):
        page = self._ensure()
        return page.locator("body").inner_text(timeout=10000)[:30000]

    def close(self):
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        self._browser = self._page = self._playwright = None
        return "Браузерный агент остановлен."
