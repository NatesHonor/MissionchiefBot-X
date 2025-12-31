import re
import json
import os
from utils.pretty_print import display_info, display_error
from .helpers import get_val, normalize_name
from .requirements import gather_requirements
from .prisoners import handle_prisoner_transport

_LOCKED_VEHICLES = {}

def free_up_vehicles(mission_id):
    global _LOCKED_VEHICLES
    _LOCKED_VEHICLES = {vid: mid for vid, mid in _LOCKED_VEHICLES.items() if mid != mission_id}
    display_info(f"Freeing up mission: {mission_id}")

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
    normalized = raw_name.lower().replace(",", " or ")
    parts = [p.strip() for p in normalized.split(" or ") if p.strip()]
    opts = [resolve_vehicle_name(normalize_name(p)) for p in parts]
    return {"options": opts, "count": count}

async def gather_mission_info(ids, context, tid):
    data = {}
    old_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cache", "mission_data.json")
    old_ids = set()
    if os.path.exists(old_file):
        try:
            with open(old_file, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                old_ids = set(old_data.keys())
        except:
            old_ids = set()
    new_ids = set(ids)
    removed_ids = old_ids - new_ids
    for rid in removed_ids:
        free_up_vehicles(rid)
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
            requirements_handled = False
            missing_alerts = await page.query_selector_all("div.alert-missing-vehicles div[data-requirement-type='personnel']")
            if missing_alerts:
                personnel_reqs = []
                for alert in missing_alerts:
                    text = (await alert.inner_text()).strip()
                    m = re.match(r".*?(\d+)\s+(.+)", text)
                    if m:
                        count = int(m.group(1))
                        role = normalize_name(m.group(2))
                        personnel_reqs.append({"name": role, "count": count})
                data[mid] = {
                    "mission_name": name,
                    "credits": 0,
                    "vehicles": [],
                    "personnel": personnel_reqs,
                    "liquid": [],
                    "patients": 0,
                    "crashed_cars": 0,
                }
                requirements_handled = True
            if not requirements_handled:
                for alert in await page.query_selector_all("div.alert.alert-danger"):
                    txt = (await alert.inner_text()).lower()
                    if "prisoners must be transported" in txt or "transport is needed!" in txt:
                        if not await handle_prisoner_transport(page):
                            result = await page.evaluate("""() => {
                                const h4 = document.querySelector("#h2_prisoners");
                                let prisoners = 0;
                                if (h4) {
                                    const m = h4.textContent.match(/(\\d+)/);
                                    if (m) prisoners = parseInt(m[1]);
                                }
                                const rows = document.querySelectorAll("#mission_vehicle_at_mission tbody tr small.vehicle_caption");
                                const captions = Array.from(rows).map(el => el.textContent.toLowerCase());
                                return { prisoners, captions };
                            }""")
                            cnt = result["prisoners"]
                            captions = result["captions"]
                            covered = sum(1 for c in captions if "patrol car" in c or "supervisor" in c or "sheriff" in c)
                            remaining = max(0, cnt - covered)
                            vehicles_needed = []
                            if remaining > 0:
                                if remaining < 4:
                                    vehicles_needed.append({"options": ["police car"], "count": remaining})
                                else:
                                    vans = (remaining + 3) // 4
                                    vehicles_needed.append({"options": ["prisoner transport van"], "count": vans})
                            data[mid] = {
                                "mission_name": f"Prisoner Transport Mission {mid}",
                                "credits": 0,
                                "vehicles": vehicles_needed,
                                "personnel": [],
                                "liquid": [],
                                "patients": 0,
                                "crashed_cars": 0,
                            }
                            requirements_handled = True
                            break
            if requirements_handled:
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
