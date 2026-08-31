import asyncio

from utils.pretty_print import display_error, display_info


async def load_mission_page(page, mission_id, name, url):
    mission_url = f"{url.rstrip('/')}/missions/{mission_id}"
    for attempt in range(2):
        try:
            display_info(f"Navigating: {mission_url} (Attempt {attempt + 1})")
            await page.goto(mission_url, wait_until="domcontentloaded", timeout=10000)
            await page.wait_for_selector("#missionH1", timeout=10000)
            await page.wait_for_selector("#alert_btn", timeout=10000)
            display_info(f"Loaded mission {name} ({mission_id})")
            return True
        except Exception as error:
            display_error(f"Load attempt {attempt + 1} failed for mission {mission_id}: {error}")
            if attempt == 1:
                display_error(f"Failed loading mission {mission_id}, skipping.")
                return False
            await asyncio.sleep(2)
    return False
