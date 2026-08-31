"""Mission page parser shared by supported region adapters."""

from __future__ import annotations

import json
import re

from utils.pretty_print import display_error, display_info

from .mission_helpers import get_val, normalize_name
from .localization import contains_localized_term
from .mission_prisoners import handle_prisoner_transport
from .mission_requirements import gather_requirements
from .pages import ensure_page
from .regions import get_region_profile
from .vehicle_state import get_vehicle_state


def free_up_vehicles(mission_id, profile=None, state=None):
    state = state or get_vehicle_state(profile or get_region_profile())
    state.free_for_mission(mission_id)


def load_vehicle_aliases(profile=None):
    profile = profile or get_region_profile()
    try:
        with profile.vehicle_aliases_file.open("r", encoding="utf-8") as stream:
            return json.load(stream)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def resolve_vehicle_name(name: str, profile=None) -> str:
    normalized = name.lower()
    for canonical, synonyms in load_vehicle_aliases(profile).items():
        if normalized == canonical.lower() or normalized in [synonym.lower() for synonym in synonyms]:
            return canonical
    return normalized


def resolve_vehicle_entry(raw_name: str, count: int, profile=None):
    normalized = raw_name.lower().replace(",", " or ")
    parts = [part.strip() for part in normalized.split(" or ") if part.strip()]
    options = [resolve_vehicle_name(normalize_name(part), profile) for part in parts]
    return {"options": options, "count": count}


async def gather_mission_info(ids, context, tid, url, profile=None, state=None):
    profile = profile or get_region_profile()
    state = state or get_vehicle_state(profile)
    data = {}

    old_ids = set()
    if profile.mission_file.exists():
        try:
            with profile.mission_file.open("r", encoding="utf-8") as stream:
                old_ids = set(json.load(stream).keys())
        except (OSError, json.JSONDecodeError, AttributeError):
            old_ids = set()
    for removed_id in old_ids - set(ids):
        state.free_for_mission(removed_id)

    page = await ensure_page(context)
    for index, mission_id in enumerate(ids):
        try:
            display_info(f"Thread {tid}: Grabbing missions {index + 1}/{len(ids)}")
            await page.goto(f"{url.rstrip('/')}/missions/{mission_id}")
            await page.wait_for_selector("#missionH1", timeout=5000)
            name_element = await page.query_selector("#missionH1")
            if not name_element:
                continue
            name = (await name_element.inner_text()).strip()
            requirements_handled = False

            missing_alerts = await page.query_selector_all(
                "div.alert-missing-vehicles div[config-requirement-type='personnel']"
            )
            if missing_alerts:
                personnel = []
                for alert in missing_alerts:
                    match = re.match(r".*?(\d+)\s+(.+)", (await alert.inner_text()).strip())
                    if match:
                        personnel.append(
                            {
                                "name": normalize_name(match.group(2)),
                                "count": int(match.group(1)),
                            }
                        )
                data[mission_id] = {
                    "mission_name": name,
                    "credits": 0,
                    "vehicles": [],
                    "personnel": personnel,
                    "liquid": [],
                    "patients": 0,
                    "crashed_cars": 0,
                }
                requirements_handled = True

            if not requirements_handled:
                for alert in await page.query_selector_all("div.alert.alert-danger"):
                    text = (await alert.inner_text()).lower()
                    if not contains_localized_term(
                        text, profile.language, "prisoner_transport"
                    ):
                        continue
                    if not await handle_prisoner_transport(page):
                        result = await page.evaluate(
                            """() => {
                                const h4 = document.querySelector('#h2_prisoners');
                                let prisoners = 0;
                                if (h4) {
                                    const m = h4.textContent.match(/(\\d+)/);
                                    if (m) prisoners = parseInt(m[1]);
                                }
                                const rows = document.querySelectorAll(
                                    '#mission_vehicle_at_mission tbody tr small.vehicle_caption'
                                );
                                const captions = Array.from(rows).map(
                                    el => el.textContent.toLowerCase()
                                );
                                return { prisoners, captions };
                            }"""
                        )
                        remaining = max(
                            0,
                            result["prisoners"]
                            - sum(
                                1
                                for caption in result["captions"]
                                if "patrol car" in caption
                                or "supervisor" in caption
                                or "sheriff" in caption
                            ),
                        )
                        vehicles = []
                        if remaining > 0:
                            if remaining < 4:
                                vehicles.append({"options": ["police car"], "count": remaining})
                            else:
                                vehicles.append(
                                    {
                                        "options": ["prisoner transport van"],
                                        "count": (remaining + 3) // 4,
                                    }
                                )
                        data[mission_id] = {
                            "mission_name": f"Prisoner Transport Mission {mission_id}",
                            "credits": 0,
                            "vehicles": vehicles,
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
            requirements = await gather_requirements(page, profile)
            credits = await get_val(
                page,
                [
                    'td:has-text("Average credits") + td',
                    'td:has-text("Durchschnittliche Credits") + td',
                    'td:has-text("Durchschnittliche Kredite") + td',
                ],
                True,
            )
            patients = await get_val(
                page,
                [
                    'td:has-text("Max. Patients") + td',
                    'td:has-text("Max. Patienten") + td',
                    'td:has-text("Maximale Patienten") + td',
                ],
            )
            crashed = await get_val(
                page,
                [
                    'td:has-text("Maximum amount of cars to tow") + td',
                    'td:has-text("Maximale Anzahl abzuschleppender Fahrzeuge") + td',
                    'td:has-text("Abzuschleppende Fahrzeuge") + td',
                ],
            )
            if patients:
                requirements["vehicles"].append({"name": "ambulance", "count": patients})
                if patients >= 10:
                    requirements["vehicles"].append({"name": "ems chief", "count": 1})
                if patients >= 20:
                    requirements["vehicles"].append(
                        {"name": "ems mobile command unit", "count": 1}
                    )

            vehicles, liquid = [], []
            for vehicle in requirements["vehicles"]:
                entry = resolve_vehicle_entry(vehicle["name"], vehicle["count"], profile)
                if any(option.lower() == "water" for option in entry["options"]):
                    liquid.append(entry)
                else:
                    vehicles.append(entry)
            data[mission_id] = {
                "mission_name": name,
                "credits": credits,
                "vehicles": vehicles,
                "personnel": requirements["personnel"],
                "liquid": liquid,
                "patients": patients,
                "crashed_cars": crashed,
            }
        except Exception as error:
            display_error(f"Error processing mission ID {mission_id}: {error}")
    return data
