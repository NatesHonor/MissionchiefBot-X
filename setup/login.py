import asyncio
from playwright.async_api import async_playwright
from data.config_settings import get_username, get_password, get_threads, get_headless
from utils.pretty_print import display_message, display_error
import sys

async def login_single(username, password, headless, thread_id):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()
        await page.goto("https://www.missionchief.com/users/sign_in")
        await page.wait_for_selector("form#new_user")
        await page.fill('input[name="user[email]"]', username)
        await page.fill('input[name="user[password]"]', password)
        await page.click('input[type="submit"]')
        await page.wait_for_load_state("networkidle")
        error_message = page.locator('text=Invalid email or password')
        if await error_message.is_visible():
            return "Failure", f"Thread {thread_id}: Invalid email or password", browser
        return "Success", thread_id, browser


async def login():
    username = get_username()
    password = get_password()
    headless = get_headless()
    threads = get_threads()
    tasks = [login_single(username, password, headless, thread_id) for thread_id in range(1, threads + 1)]
    results = await asyncio.gather(*tasks)
    failed_logins = sum(1 for result in results if result[0] == "Failure")
    error_messages = [result[1] for result in results if result[0] == "Failure"]
    successful_logins = [result[1] for result in results if result[0] == "Success"]
    browsers = [result[2] for result in results if result[0] == "Success"]
    if failed_logins > 0:
        display_message("ERROR!")
        display_error(f"{failed_logins}/{threads} drivers failed to log in.")
        display_error(f"The bot has gathered the following error(s): {', '.join(set(error_messages))}")
        sys.exit(1)

    display_message(f"All {threads} logins completed successfully.")

    return successful_logins, browsers
