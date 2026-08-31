"""Browser lifecycle management shared by every region."""

from __future__ import annotations

import asyncio
from typing import Any


class BrowserPool:
    """Launch and own a fixed set of Playwright browsers.

    Contexts are owned by the caller; browser processes are owned here.  A
    browser may be returned to the pool after a context is created because
    Playwright supports multiple isolated contexts per browser.
    """

    def __init__(self, playwright: Any, size: int, headless: bool):
        if size < 1:
            raise ValueError("Browser pool size must be at least 1.")
        self.playwright = playwright
        self.size = size
        self.headless = headless
        self._queue: asyncio.Queue[Any] = asyncio.Queue()
        self._browsers: list[Any] = []
        self._started = False
        self._closed = False

    async def start(self) -> None:
        if self._started:
            return
        try:
            for _ in range(self.size):
                browser = await self.playwright.chromium.launch(
                    headless=self.headless,
                )
                self._browsers.append(browser)
                await self._queue.put(browser)
        except Exception:
            await self.close_all()
            raise
        self._started = True

    async def acquire(self) -> Any:
        if not self._started or self._closed:
            raise RuntimeError("Browser pool is not available.")
        return await self._queue.get()

    async def release(self, browser: Any) -> None:
        if self._closed:
            await browser.close()
            return
        await self._queue.put(browser)

    async def close_all(self) -> None:
        if self._closed:
            return
        self._closed = True
        while not self._queue.empty():
            await self._queue.get()
        for browser in self._browsers:
            try:
                await browser.close()
            except Exception:
                pass
        self._browsers.clear()
