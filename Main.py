import asyncio
import os
from playwright.async_api import async_playwright

from data.region_tracker import get_url, setup_region
from missions.buildings import gather_building_data
from utils.tasks import grab_tasks
from setup.login_manager import BrowserPool, login_single
from data.config_settings import (
    get_username,
    get_password,
    get_threads,
    get_headless,
    get_mission_delay,
    get_other_delay,
    get_concurrent_missions,
    get_auto_tasks,
    get_dispatch_type
)
from dispatching import navigate_and_dispatch
from missions import check_and_grab_missions
from utils.pretty_print import display_info, display_error
from utils.transport import handle_transport_requests
from utils.vehicle_data import gather_vehicle_data

async def other_logic(context, url):
    display_info("Starting transportation logic.")
    while True:
        try:
            await handle_transport_requests(context, url)
            if get_auto_tasks():
                await grab_tasks(context, url)
            await asyncio.sleep(get_other_delay())
        except Exception as e:
            display_error(f"Error in transport logic: {e}")


async def mission_logic(grabbing_contexts, dispatch_contexts, url):
    display_info("Starting mission logic.")
    while True:
        try:
            if not os.path.exists("data/vehicle_data.json"):
                await gather_vehicle_data(grabbing_contexts, len(grabbing_contexts), url)
            if not os.path.exists("data/building_data.json"):
                await gather_building_data(grabbing_contexts, len(grabbing_contexts), url)

            await check_and_grab_missions(grabbing_contexts, len(grabbing_contexts), url)
            await navigate_and_dispatch(dispatch_contexts, url)
            await asyncio.sleep(get_mission_delay())
        except Exception as e:
            display_error(f"Error in mission logic: {e}")


async def main():
    setup_region()

    username = get_username()
    password = get_password()
    threads = get_threads()
    headless = get_headless()
    url = get_url()
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
                browser_pool=browser_pool,
                url=url
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

        concurrent = get_concurrent_missions()
        dispatch_type = get_dispatch_type()
        display_info("Pooled settings:")
        display_info(f"Headless browsers: {'enabled' if headless else 'disabled'}.")
        display_info(f"Thread Count: {threads}")
        display_info(f"Dispatch type: {dispatch_type}.")
        display_info(f"Concurrent missions are currently {'enabled' if concurrent else 'disabled'}.")

        other_context = contexts[0]
        grabbing_contexts = contexts[1:]
        if concurrent:
            mission_contexts = grabbing_contexts
        else:
            mission_contexts = grabbing_contexts[:1]

        mission_task = asyncio.create_task(mission_logic(grabbing_contexts, mission_contexts, url))
        other_task = asyncio.create_task(other_logic(other_context, url))

        await asyncio.gather(mission_task, other_task)

        for ctx in contexts:
            await ctx.close()

        await browser_pool.close_all()

if __name__ == "__main__":
    asyncio.run(main())
