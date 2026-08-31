"""MissionChief login workflow shared by all supported regions."""

from __future__ import annotations

import asyncio

from utils.pretty_print import display_error, display_info, display_warning


MAX_RETRIES = 3


async def login_single(
    username,
    password,
    thread_id,
    delay,
    browser_pool,
    url,
):
    """Login one isolated context and return the legacy result tuple."""

    if delay:
        await asyncio.sleep(delay)

    for attempt in range(1, MAX_RETRIES + 1):
        browser = None
        context = None
        keep_context = False
        try:
            display_info(f"Thread {thread_id}: Login attempt {attempt}")
            browser = await browser_pool.acquire()
            context = await browser.new_context()
            page = await context.new_page()

            await page.goto(
                f"{url.rstrip('/')}/users/sign_in",
                wait_until="domcontentloaded",
            )
            await page.wait_for_selector("form#new_user", timeout=5000)
            await page.fill('input[name="user[email]"]', username)
            await page.fill('input[name="user[password]"]', password)
            await page.click('input[type="submit"]')
            await page.wait_for_load_state("networkidle", timeout=10000)

            if await page.locator("iframe[src*='captcha']").count() > 0:
                display_warning(f"Thread {thread_id}: CAPTCHA detected")
                raise RuntimeError("CAPTCHA detected")

            if await page.locator("text=Invalid email or password").count() > 0:
                display_error(f"Thread {thread_id}: Invalid credentials")
                return "Failure", "Invalid credentials", None

            if url.rstrip("/") not in page.url:
                raise RuntimeError(f"Unexpected domain after login: {page.url}")

            display_info(f"Thread {thread_id}: Login successful")
            keep_context = True
            return "Success", thread_id, context
        except Exception as error:
            display_warning(f"Thread {thread_id}: Attempt {attempt} failed ({error})")
            if attempt == MAX_RETRIES:
                display_error(f"Thread {thread_id}: Login failed after retries")
                return "Failure", str(error), None
            await asyncio.sleep(2)
        finally:
            if context and not keep_context:
                await context.close()
            if browser:
                await browser_pool.release(browser)
