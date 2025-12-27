import asyncio
import os
from playwright.async_api import async_playwright
from setup.login_manager import BrowserPool, login_single
from data.config_settings import (
    get_username,
    get_password,
    get_threads,
    get_headless,
    get_mission_delay,
    get_transport_delay
)
from dispatching import navigate_and_dispatch
from missions import check_and_grab_missions
from utils.pretty_print import display_info, display_error
from utils.transport import handle_transport_requests
from utils.vehicle_data import gather_vehicle_data


async def transport_logic(context):
    display_info("Starting transportation logic.")
    while True:
        try:
            await handle_transport_requests(context)
            await asyncio.sleep(get_transport_delay())
        except Exception as e:
            display_error(f"Error in transport logic: {e}")


async def mission_logic(contexts):
    display_info("Starting mission logic.")
    while True:
        try:
            if os.path.exists("data/vehicle_data.json"):
                await check_and_grab_missions(contexts, len(contexts))
            else:
                await gather_vehicle_data(contexts, len(contexts))
                await check_and_grab_missions(contexts, len(contexts))

            await navigate_and_dispatch(contexts)
            await asyncio.sleep(get_mission_delay())
        except Exception as e:
            display_error(f"Error in mission logic: {e}")


async def main():
    username = get_username()
    password = get_password()
    threads = get_threads()
    headless = get_headless()

    async with async_playwright() as p:
        browser_pool = BrowserPool(
            playwright=p,
            size=threads,
            headless=headless
        )
        await browser_pool.start()

        login_tasks = [
            login_single(
                username=username,
                password=password,
                thread_id=i + 1,
                delay=i * 1.5,
                browser_pool=browser_pool
            )
            for i in range(threads)
        ]

        results = await asyncio.gather(*login_tasks)

        contexts = []
        for status, info, ctx in results:
            if status == "Success":
                contexts.append(ctx)
            else:
                display_error(f"Login failed: {info}")

        if len(contexts) < 2:
            display_error("Not enough successful logins to start automation.")
            await browser_pool.close_all()
            return

        transport_context = contexts[0]
        mission_contexts = contexts[1:]

        mission_task = asyncio.create_task(mission_logic(mission_contexts))
        transport_task = asyncio.create_task(transport_logic(transport_context))

        await asyncio.gather(mission_task, transport_task)

        for ctx in contexts:
            await ctx.close()

        await browser_pool.close_all()


if __name__ == "__main__":
    asyncio.run(main())
