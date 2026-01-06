import asyncio
from utils.pretty_print import display_info, display_error

async def load_mission_page(page, mission_id, name, url):
    murl = url + "missions/{mission_id}"
    for attempt in range(2):
        try:
            display_info(f"Navigating: {murl} (Attempt {attempt+1})")
            await page.goto(murl, wait_until="domcontentloaded", timeout=10000)
            await page.wait_for_selector('#missionH1', timeout=10000)
            await page.wait_for_selector('#alert_btn', timeout=10000)
            display_info(f"Loaded mission {name} ({mission_id})")
            return True
        except Exception as e:
            display_error(f"Load attempt {attempt+1} failed for mission {mission_id}: {e}")
            if attempt == 1:
                display_error(f"❌ Failed loading mission {mission_id}, skipping.")
                return False
            await asyncio.sleep(2)
    return False
