import asyncio
from utils.pretty_print import display_info, display_error

async def load_mission_page(page, mission_id, name):
    url = f"https://www.missionchief.com/missions/{mission_id}"
    for attempt in range(2):
        try:
            display_info(f"Navigating: {url} (Attempt {attempt+1})")
            await page.goto(url, wait_until="domcontentloaded", timeout=10000)
            await page.wait_for_selector('#missionH1', timeout=5000)
            display_info(f"Loaded mission {name} ({mission_id})")
            return True
        except:
            if attempt == 1:
                display_error(f"❌ Failed loading mission {mission_id}, skipping.")
                return False
            await asyncio.sleep(2)
    return False
