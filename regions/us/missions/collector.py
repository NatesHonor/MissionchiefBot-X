import json
from pathlib import Path
from config.config_settings import get_region
from utils.pretty_print import display_info, display_error
from regions.uk.utils.threading import split_mission_ids_among_threads

BASE_DIR = Path(__file__).resolve().parents[3]
REGION = get_region().lower()
DATA_DIR = BASE_DIR / "regions" / REGION / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
MISSION_FILE = DATA_DIR / "mission_data.json"

async def check_and_grab_missions(contexts, num_threads, url):
    if not isinstance(contexts, list):
        contexts = [contexts]
    if not contexts:
        return
    if not contexts[0].pages:
        await contexts[0].new_page()
    try:
        if MISSION_FILE.exists():
            MISSION_FILE.unlink()
        page = contexts[0].pages[0]
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        panels = await page.query_selector_all(".mission_panel_red")
        if not panels:
            display_info("No missions found, skipping this function.")
            return
        ids = [(await p.get_attribute("id")).split("_")[-1] for p in panels]
        display_info(f"Found {len(ids)} mission IDs.")
        data = await split_mission_ids_among_threads(ids, contexts, min(num_threads, len(contexts)), url)
        with open(MISSION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        display_info("Mission config collection complete. Stored mission config in mission_data.json.")
    except Exception as e:
        display_error(f"Error gathering mission config: {e}")