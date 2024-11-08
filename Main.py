import asyncio
import os
from playwright.async_api import async_playwright
from setup.login import login_single
from data.config_settings import get_username, get_password, get_threads, get_headless
from utils.pretty_print import display_info, display_error

async def login():
    username = get_username()
    password = get_password()
    headless = get_headless()
    threads = get_threads()
    successful_logins = []
    browsers = []

    async with async_playwright() as p:
        for thread_id in range(1, threads + 1):
            delay = (thread_id - 1) * 2
            result = await login_single(username, password, headless, thread_id, delay, p)

            if result[0] == "Success":
                successful_logins.append(result[1])
                browsers.append(result[2])
            else:
                display_error(result[1])

    if not successful_logins:
        display_error("Login failed. No threads were successfully logged in.")
        exit(1)

    display_info(f"All drivers logged in successfully. Threads: {', '.join(map(str, successful_logins))}")

    await check_vehicle_data(browsers)

    for browser in browsers:
        await browser.close()

    return successful_logins, browsers

async def check_vehicle_data(browsers):
    if not os.path.exists("data/vehicle_data.json"):
        display_info("vehicle_data.json does not exist. Navigating to Leitstellenansicht.")
        first_browser = browsers[0]
        try:
            page = await first_browser.new_page()
            await page.goto("https://www.missionchief.com/leitstellenansicht")
            await page.wait_for_load_state("networkidle")
            display_info("Successfully navigated to Leitstellenansicht.")
        except Exception as e:
            display_error(f"Error navigating to Leitstellenansicht: {e}")
            await first_browser.close()

if __name__ == "__main__":
    asyncio.run(login())
