import asyncio
from utils.pretty_print import display_info, display_error, display_warning

MAX_RETRIES = 3

class BrowserPool:
    def __init__(self, playwright, size, headless):
        self.playwright = playwright
        self.size = size
        self.headless = headless
        self._queue = asyncio.Queue()

    async def start(self):
        for _ in range(self.size):
            browser = await self.playwright.chromium.launch(
                headless=self.headless,
                devtools=False
            )
            await self._queue.put(browser)

    async def acquire(self):
        return await self._queue.get()

    async def release(self, browser):
        await self._queue.put(browser)

    async def close_all(self):
        while not self._queue.empty():
            browser = await self._queue.get()
            await browser.close()

async def login_single(
        username,
        password,
        thread_id,
        delay,
        browser_pool,
        url
):
    if delay:
        await asyncio.sleep(delay)

    for attempt in range(1, MAX_RETRIES + 1):
        browser = None
        context = None
        try:
            display_info(f"Thread {thread_id}: Login attempt {attempt}")

            browser = await browser_pool.acquire()
            context = await browser.new_context()
            page = await context.new_page()

            await page.goto(
                url + "users/sign_in",
                wait_until="domcontentloaded"
            )

            await page.wait_for_selector("form#new_user", timeout=5000)

            await page.fill('input[name="user[email]"]', username)
            await page.fill('input[name="user[password]"]', password)
            await page.click('input[type="submit"]')

            await page.wait_for_load_state("networkidle", timeout=10000)

            if await page.locator("iframe[src*='captcha']").count() > 0:
                display_warning(f"Thread {thread_id}: CAPTCHA detected")
                raise RuntimeError("CAPTCHA detected")

            if await page.locator('text=Invalid email or password').count() > 0:
                display_error(f"Thread {thread_id}: Invalid credentials")
                await context.close()
                await browser_pool.release(browser)
                return "Failure", "Invalid credentials", None

            if url not in page.url:
                raise RuntimeError(f"Unexpected domain after login: {page.url}")

            display_info(f"Thread {thread_id}: Login successful")
            await browser_pool.release(browser)
            return "Success", thread_id, context

        except Exception as e:
            display_warning(f"Thread {thread_id}: Attempt {attempt} failed ({e})")

            if context:
                await context.close()

            if browser:
                await browser_pool.release(browser)

            if attempt == MAX_RETRIES:
                display_error(f"Thread {thread_id}: Login failed after retries")
                return "Failure", str(e), None

            await asyncio.sleep(2)
