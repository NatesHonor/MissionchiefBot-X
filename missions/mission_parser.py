import re
import json
import os
from utils.pretty_print import display_info, display_error
from .helpers import get_val, normalize_name
from .requirements import gather_requirements
from .prisoners import handle_prisoner_transport

def load_vehicle_aliases():
    parent_dir = os.path.dirname(os.path.dirname(__file__))
    alias_file = os.path.join(parent_dir, "data", "vehicle_aliases.json")
    with open(alias_file, "r", encoding="utf-8") as f:
        return json.load(f)

ALIASES = load_vehicle_aliases()

def resolve_vehicle_name(name: str) -> str:
    n = name.lower()
    for canonical, synonyms in ALIASES.items():
        if n == canonical.lower() or n in [s.lower() for s in synonyms]:
            return canonical
    return n

def resolve_vehicle_entry(raw_name: str, count: int):
    if " or " in raw_name.lower():
        opts = [resolve_vehicle_name(normalize_name(x.strip())) for x in raw_name.split(" or ")]
        return {"options": opts, "count": count}
    else:
        canonical = resolve_vehicle_name(normalize_name(raw_name))
        return {"options": [canonical], "count": count}

async def gather_mission_info(ids, context, tid):
    data = {}
    if not context.pages:
        await context.new_page()
    page = context.pages[0]
    for i, mid in enumerate(ids):
        try:
            display_info(f"Thread {tid}: Grabbing missions {i+1}/{len(ids)}")
            await page.goto(f"https://www.missionchief.com/missions/{mid}")
            await page.wait_for_selector("#missionH1", timeout=5000)
            name_el = await page.query_selector("#missionH1")
            if not name_el:
                continue
            name = (await name_el.inner_text()).strip()
            crashed = 0
            prisoner_handled = False
            for alert in await page.query_selector_all("div.alert.alert-danger"):
                txt = (await alert.inner_text()).lower()
                if "prisoners must be transported" in txt or "transport is needed!" in txt:
                    if not await handle_prisoner_transport(page):
                        h4 = await page.query_selector("#h2_prisoners")
                        cnt = int(re.search(r"(\d+)", await h4.inner_text()).group(1)) if h4 else 0
                        dispatched = await page.query_selector_all("#mission_vehicle_at_mission tbody tr")
                        covered = 0
                        for row in dispatched:
                            caption_el = await row.query_selector("small.vehicle_caption")
                            if caption_el:
                                caption = (await caption_el.inner_text()).lower()
                                if "patrol car" in caption:
                                    covered += 1
                                elif "supervisor" in caption or "sheriff" in caption:
                                    covered += 1
                        remaining = max(0, cnt - covered)
                        vehicles_needed = []
                        if remaining > 0:
                            if remaining < 4:
                                vehicles_needed.append({"name": "police car", "count": remaining})
                            else:
                                vans = (remaining + 3) // 4
                                vehicles_needed.append({"name": "prisoner transport van", "count": vans})
                        data[mid] = {
                            "mission_name": f"Prisoner Transport Mission {mid}",
                            "credits": 0,
                            "vehicles": vehicles_needed,
                            "personnel": [{"name": "prisoners", "count": cnt}],
                            "liquid": [],
                            "patients": 0,
                            "crashed_cars": 0,
                        }
                        prisoner_handled = True
                        continue
            if prisoner_handled:
                continue
            await page.click("#mission_help")
            await page.wait_for_selector("#iframe-inside-container", timeout=5000)
            requirements = await gather_requirements(page)
            credits = await get_val(page, 'td:has-text("Average credits") + td', True)
            patients = await get_val(page, 'td:has-text("Max. Patients") + td')
            crashed = await get_val(page, 'td:has-text("Maximum amount of cars to tow") + td')
            if patients:
                requirements["vehicles"].append({"name": "ambulance", "count": patients})
                if patients >= 10:
                    requirements["vehicles"].append({"name": "ems chief", "count": 1})
                if patients >= 20:
                    requirements["vehicles"].append({"name": "ems mobile command unit", "count": 1})
            resolved_vehicles = []
            resolved_liquid = []
            for v in requirements["vehicles"]:
                entry = resolve_vehicle_entry(v["name"], v["count"])
                if any(opt.lower() == "water" for opt in entry["options"]):
                    resolved_liquid.append(entry)
                else:
                    resolved_vehicles.append(entry)
            data[mid] = {
                "mission_name": name,
                "credits": credits,
                "vehicles": resolved_vehicles,
                "personnel": requirements["personnel"],
                "liquid": resolved_liquid,
                "patients": patients,
                "crashed_cars": crashed,
            }
        except Exception as e:
            display_error(f"Error processing mission ID {mid}: {e}")
    return data
