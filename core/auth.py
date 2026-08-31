"""MissionChief login workflow shared by all supported regions."""

from __future__ import annotations

import asyncio
import re
from urllib.parse import urlparse

from utils.pretty_print import display_error, display_info, display_warning


MAX_RETRIES = 3
LOGIN_PATH = "/users/sign_in"
LOGIN_FAILURE_MARKERS = (
    "invalid email or password",
    "invalid username or password",
    "invalid credentials",
    "incorrect email or password",
    "email or password is incorrect",
    "ungültige email oder passwort",
    "falsche email oder passwort",
    "mot de passe ou email incorrect",
    "contraseña o correo incorrectos",
    "senha ou email incorretos",
    "ogiltig e-postadress eller lösenord",
    "ongeldig e-mailadres of wachtwoord",
    "forkert email eller adgangskode",
)


def _normalized_host(hostname: str | None) -> str:
    host = (hostname or "").casefold().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def is_same_service(url: str, candidate: str) -> bool:
    """Allow normal www redirects without accepting an unrelated host."""

    expected = urlparse(url)
    actual = urlparse(candidate)
    if expected.scheme not in {"http", "https"} or actual.scheme not in {"http", "https"}:
        return False
    return (
        _normalized_host(expected.hostname) == _normalized_host(actual.hostname)
        and expected.port == actual.port
    )


def is_login_page(url: str) -> bool:
    """Return whether a URL still points to the MissionChief sign-in page."""

    return urlparse(url).path.rstrip("/").casefold() == LOGIN_PATH


def classify_login_failure(text: str) -> str | None:
    """Return a stable failure reason for common localized auth messages."""

    normalized = re.sub(r"\s+", " ", str(text or "").casefold()).strip()
    if any(marker in normalized for marker in LOGIN_FAILURE_MARKERS):
        return "Invalid credentials"
    return None


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
                f"{url.rstrip('/')}{LOGIN_PATH}",
                wait_until="domcontentloaded",
            )
            await page.wait_for_selector("form#new_user", timeout=5000)
            await page.locator('input[name="user[email]"], input[type="email"]').first.fill(username)
            await page.locator('input[name="user[password]"], input[type="password"]').first.fill(password)
            await page.click('input[type="submit"]')
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception as wait_error:
                display_warning(
                    f"Thread {thread_id}: Login navigation did not reach network idle ({wait_error}); checking the page state"
                )

            if await page.locator("iframe[src*='captcha']").count() > 0:
                display_warning(f"Thread {thread_id}: CAPTCHA detected")
                raise RuntimeError("CAPTCHA detected")

            body_text = await page.locator("body").inner_text(timeout=3000)
            failure_reason = classify_login_failure(body_text)
            if failure_reason:
                display_error(f"Thread {thread_id}: Invalid credentials")
                return "Failure", failure_reason, None

            if not is_same_service(url, page.url):
                raise RuntimeError(f"Unexpected domain after login: {page.url}")
            if is_login_page(page.url) or await page.locator("form#new_user").count() > 0:
                raise RuntimeError("Login form is still visible after submitting credentials")

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
