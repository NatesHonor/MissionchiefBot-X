import asyncio
import os
import json
from playwright.async_api import async_playwright
from setup.login import login_single
from data.config_settings import get_username, get_password, get_threads, get_headless
from utils.mission_data import check_and_grab_missions
from utils.pretty_print import display_info, display_error
from utils.vehicle_data import gather_vehicle_data


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

        if os.path.exists("data/vehicle_data.json"):
            await check_and_grab_missions(browsers, threads)
        else:
            await gather_vehicle_data(browsers, threads)

        for browser in browsers:
            display_info(f"Closing browser for thread: {successful_logins[browsers.index(browser)]}")
            await browser.close()

    return successful_logins, browsers


if __name__ == "__main__":
    asyncio.run(login())
