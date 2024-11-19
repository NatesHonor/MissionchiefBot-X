import asyncio
import os
from playwright.async_api import async_playwright
from setup.login import login_single
from data.config_settings import get_username, get_password, get_threads, get_headless
from utils.dispatcher import navigate_and_dispatch
from utils.mission_data import check_and_grab_missions
from utils.pretty_print import display_info, display_error
from utils.transport import handle_transport_requests
from utils.vehicle_data import gather_vehicle_data


async def transport_logic(browser):
    display_info("Starting transportation logic.")
    while True:
        try:
            display_info("Handling transport requests.")
            await handle_transport_requests(browser)
            display_info("Waiting for 3 minutes before the next transport.")
            await asyncio.sleep(180)
        except Exception as e:
            display_error(f"Error in transport logic: {e}")


async def mission_logic(browsers_for_missions):
    display_info("Starting mission logic.")
    while True:
        try:
            if os.path.exists("data/vehicle_data.json"):
                display_info("Vehicle data exists, checking and grabbing missions.")
                await check_and_grab_missions(browsers_for_missions, len(browsers_for_missions))
            else:
                display_info("Vehicle data not found, gathering vehicle data.")
                await gather_vehicle_data(browsers_for_missions, len(browsers_for_missions))
                await check_and_grab_missions(browsers_for_missions, len(browsers_for_missions))
            display_info("Navigating and dispatching missions.")
            await navigate_and_dispatch(browsers_for_missions)
            display_info("Waiting for 10 seconds before checking missions again.")
            await asyncio.sleep(10)
        except Exception as e:
            display_error(f"Error in mission logic: {e}")

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
                display_info(f"Login successful for browser {thread_id}.")
            else:
                display_error(f"Login failed for browser {thread_id}: {result[1]}")

        if not successful_logins:
            display_error("Login failed. No browser were successfully logged in.")
            exit(1)
        display_info(f"All drivers logged in successfully. Threads: {', '.join(map(str, successful_logins))}")
        if len(browsers) < 2:
            display_error("Not enough browsers for both mission and transport logic.")
            exit(1)
        browser_for_transport = browsers[0]
        browsers_for_missions = browsers[1:]
        mission_task = asyncio.create_task(mission_logic(browsers_for_missions))
        transport_task = asyncio.create_task(transport_logic(browser_for_transport))
        await asyncio.gather(mission_task, transport_task)
        for browser in browsers:
            display_info(f"Closing browser for thread: {successful_logins[browsers.index(browser)]}")
            await browser.close()

    return successful_logins, browsers

if __name__ == "__main__":
    asyncio.run(login())
