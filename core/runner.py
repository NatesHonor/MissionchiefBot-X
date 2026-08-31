"""Application orchestration shared by every supported region."""

from __future__ import annotations

import asyncio

from utils.pretty_print import display_error, display_info
from utils.tasks import grab_tasks
from utils.transport import handle_transport_requests
from utils.vehicle_data import gather_vehicle_data

from .auth import login_single
from .browser import BrowserPool
from .buildings import gather_building_data
from .dispatching import navigate_and_dispatch
from .mission_collector import check_and_grab_missions
from .regions import RegionProfile, get_region_profile
from .settings import Settings, load_settings
from .vehicle_state import get_vehicle_state


async def _sleep_or_stop(seconds: int, stop_event: asyncio.Event) -> None:
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=max(0.1, seconds))
    except asyncio.TimeoutError:
        pass


async def run_transport_loop(context, profile: RegionProfile, settings: Settings, stop_event):
    display_info("Starting transportation logic.")
    while not stop_event.is_set():
        try:
            await handle_transport_requests(context, profile.base_url)
            if settings.auto_tasks:
                await grab_tasks(context, profile.base_url)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            display_error(f"Error in transport logic: {error}")
            await _sleep_or_stop(min(max(settings.other_delay, 1), 30), stop_event)
            continue
        await _sleep_or_stop(settings.other_delay, stop_event)


async def run_mission_loop(
    grabbing_contexts,
    dispatch_contexts,
    profile: RegionProfile,
    settings: Settings,
    state,
    stop_event,
):
    display_info("Starting mission logic.")
    while not stop_event.is_set():
        try:
            if not profile.vehicle_file.exists():
                await gather_vehicle_data(
                    grabbing_contexts,
                    len(grabbing_contexts),
                    profile.base_url,
                    profile.vehicle_file,
                )
            if not profile.building_file.exists():
                await gather_building_data(
                    grabbing_contexts,
                    len(grabbing_contexts),
                    profile.base_url,
                    profile=profile,
                )
            await check_and_grab_missions(
                grabbing_contexts,
                len(grabbing_contexts),
                profile.base_url,
                profile,
                state,
            )
            await navigate_and_dispatch(
                dispatch_contexts,
                profile.base_url,
                profile,
                state,
                settings,
            )
        except asyncio.CancelledError:
            raise
        except Exception as error:
            display_error(f"Error in mission logic: {error}")
            await _sleep_or_stop(min(max(settings.mission_delay, 1), 30), stop_event)
            continue
        await _sleep_or_stop(settings.mission_delay, stop_event)


async def run_bot(settings: Settings | None = None, profile: RegionProfile | None = None):
    """Start the bot for one validated settings/profile snapshot."""

    settings = settings or load_settings()
    profile = profile or get_region_profile(settings.region)
    if not profile.runtime_supported:
        raise RuntimeError(
            f"The {profile.key.upper()} region has metadata but no automation adapter yet."
        )
    profile.ensure_data_dir()
    state = get_vehicle_state(profile)
    state.clear_locks()
    stop_event = asyncio.Event()
    browser_pool = None
    contexts = []
    loop_tasks = []

    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        try:
            browser_pool = BrowserPool(playwright, settings.browsers, settings.headless)
            await browser_pool.start()
            login_results = await asyncio.gather(
                *(
                    login_single(
                        username=settings.username,
                        password=settings.password,
                        thread_id=index + 1,
                        delay=index * 1.5,
                        browser_pool=browser_pool,
                        url=profile.base_url,
                    )
                    for index in range(settings.browsers)
                )
            )
            for status, info, context in login_results:
                if status == "Success" and context:
                    contexts.append(context)
                else:
                    display_error(f"Login failed: {info}")

            if len(contexts) < 2:
                display_error("Not enough successful logins to start automation.")
                return

            display_info("Pooled settings:")
            display_info(f"Region: {profile.key.upper()}")
            display_info(f"Headless browsers: {'enabled' if settings.headless else 'disabled'}.")
            display_info(f"Browser count: {settings.browsers}")
            display_info(f"Dispatch type: {settings.dispatch_type}.")
            display_info(
                f"Concurrent missions are currently {'enabled' if settings.concurrent_missions else 'disabled'}."
            )

            other_context = contexts[0]
            grabbing_contexts = contexts[1:]
            mission_contexts = (
                grabbing_contexts if settings.concurrent_missions else grabbing_contexts[:1]
            )
            loop_tasks = [
                asyncio.create_task(
                    run_mission_loop(
                        grabbing_contexts,
                        mission_contexts,
                        profile,
                        settings,
                        state,
                        stop_event,
                    )
                ),
                asyncio.create_task(
                    run_transport_loop(other_context, profile, settings, stop_event)
                ),
            ]
            await asyncio.gather(*loop_tasks)
        finally:
            stop_event.set()
            for task in loop_tasks:
                if not task.done():
                    task.cancel()
            if loop_tasks:
                await asyncio.gather(*loop_tasks, return_exceptions=True)
            for context in contexts:
                try:
                    await context.close()
                except Exception:
                    pass
            if browser_pool:
                await browser_pool.close_all()
