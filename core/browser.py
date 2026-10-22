"""Lightweight browser management shared by every region.

The bot used to launch one full Chromium process per configured "browser".
Each process carried its own GPU, network and renderer overhead, so memory
grew by hundreds of megabytes per browser.

Now a single Chromium process is launched and every login gets its own
isolated *context* inside it. Contexts keep separate cookies, storage and
sessions, exactly like separate browsers, but share one engine. On top of that:

* low-memory Chromium flags disable GPU, extensions, background networking and
  other features the bot never uses;
* images, fonts, media and tracking requests are blocked, since the bot only
  reads page structure and the MissionChief APIs;
* a small viewport keeps layout and rendering cheap.
"""

from __future__ import annotations

import asyncio
from typing import Any

# Chromium switches that cut memory and CPU without affecting page logic.
LEAN_ARGS: tuple[str, ...] = (
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-breakpad",
    "--disable-component-update",
    "--disable-default-apps",
    "--disable-domain-reliability",
    "--disable-features=Translate,MediaRouter,OptimizationHints,AutofillServerCommunication,CalculateNativeWinOcclusion",
    "--disable-hang-monitor",
    "--disable-ipc-flooding-protection",
    "--disable-popup-blocking",
    "--disable-prompt-on-repost",
    "--disable-sync",
    "--metrics-recording-only",
    "--mute-audio",
    "--no-default-browser-check",
    "--no-first-run",
    "--password-store=basic",
    "--use-mock-keychain",
    "--js-flags=--max-old-space-size=256",
)

# Resource types the bot never needs. Scripts, documents, XHR/fetch and
# stylesheets are kept: the game's UI and APIs depend on them.
BLOCKED_RESOURCES = frozenset({"image", "media", "font", "texttrack", "eventsource", "manifest"})

# Third-party hosts that only add tracking, ads or analytics.
BLOCKED_HOSTS: tuple[str, ...] = (
    "google-analytics.com",
    "googletagmanager.com",
    "doubleclick.net",
    "googlesyndication.com",
    "facebook.net",
    "hotjar.com",
)

VIEWPORT = {"width": 1280, "height": 800}


async def ensure_page(context: Any) -> Any:
    """Reuse a context's first page instead of opening extra tabs."""

    if context.pages:
        return context.pages[0]
    return await context.new_page()


async def _block_heavy_requests(route: Any) -> None:
    request = route.request
    if request.resource_type in BLOCKED_RESOURCES or any(host in request.url for host in BLOCKED_HOSTS):
        await route.abort()
    else:
        await route.continue_()


class BrowserPool:
    """One shared Chromium process handing out isolated, lightweight contexts.

    ``acquire()`` returns an object with ``new_context()`` so existing callers
    keep working unchanged; every context it creates is lean by default.
    ``size`` limits how many logins run at the same time.
    """

    def __init__(self, playwright: Any, size: int, headless: bool):
        if size < 1:
            raise ValueError("Browser pool size must be at least 1.")
        self.playwright = playwright
        self.size = size
        self.headless = headless
        self._browser: Any = None
        self._slots: asyncio.Semaphore | None = None
        self._closed = False

    async def start(self) -> None:
        if self._browser is not None:
            return
        self._browser = await self.playwright.chromium.launch(headless=self.headless, args=list(LEAN_ARGS))
        self._slots = asyncio.Semaphore(self.size)

    async def acquire(self) -> "_LeanBrowser":
        if self._browser is None or self._closed or self._slots is None:
            raise RuntimeError("Browser pool is not available.")
        await self._slots.acquire()
        return _LeanBrowser(self._browser)

    async def release(self, browser: Any) -> None:
        if self._slots is not None and not self._closed:
            self._slots.release()

    async def close_all(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None


class _LeanBrowser:
    """Shares the pool's Chromium process; creates contexts with savings applied."""

    def __init__(self, browser: Any):
        self._browser = browser

    async def new_context(self, **options: Any) -> Any:
        options.setdefault("viewport", VIEWPORT)
        options.setdefault("service_workers", "block")
        context = await self._browser.new_context(**options)
        await context.route("**/*", _block_heavy_requests)
        return context

    async def close(self) -> None:
        # The shared process is owned by BrowserPool; closing a handle is a no-op.
        return None

    def __getattr__(self, name: str) -> Any:
        return getattr(self._browser, name)
