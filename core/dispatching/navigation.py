import asyncio

from utils.pretty_print import display_error, display_info


async def load_mission_page(page, mission_id, name, url):
    mission_url = f"{url.rstrip('/')}/missions/{mission_id}"
    for attempt in range(3):
        try:
            display_info(f"Navigating: {mission_url} (Attempt {attempt + 1})")
            await page.goto(mission_url, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_selector("#missionH1", timeout=15000)
            await page.wait_for_selector("#alert_btn", timeout=10000)
            display_info(f"Loaded mission {name} ({mission_id})")
            return True
        except Exception as error:
            short_error = str(error).splitlines()[0].strip() or type(error).__name__
            display_error(
                f"Load attempt {attempt + 1} failed for mission {mission_id}: "
                f"{type(error).__name__}: {short_error}"
            )
            if attempt == 2:
                display_error(f"Failed loading mission {mission_id}, skipping.")
                return False
            await asyncio.sleep(attempt + 1)
    return False
