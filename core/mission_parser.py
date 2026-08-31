"""Mission page parser shared by supported region adapters."""

from __future__ import annotations

import json
import re
import unicodedata

from utils.pretty_print import display_error, display_info

from .mission_helpers import get_val, normalize_name
from .localization import contains_localized_term, get_localized_terms
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
    return profile.vehicle_aliases()


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(character for character in value if not unicodedata.combining(character))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]+", " ", value.casefold())).strip()


def resolve_vehicle_name(name: str, profile=None) -> str:
    profile = profile or get_region_profile()
    normalized = _normalize(name)
    for canonical, synonyms in load_vehicle_aliases(profile).items():
        if normalized in {_normalize(canonical), *(_normalize(synonym) for synonym in synonyms)}:
            return canonical
    return normalized


def resolve_vehicle_entry(raw_name: str, count: int, profile=None):
    profile = profile or get_region_profile()
    normalized = str(raw_name or "").casefold().replace(",", " or ")
    parts = [part.strip() for part in normalized.split(" or ") if part.strip()]
    options = [
        resolve_vehicle_name(normalize_name(part, profile.language), profile)
        for part in parts
    ]
    return {"options": options, "count": count}


def _value_selectors(profile, category):
    """Build selectors from the localized label catalog plus English fallback."""

    return [
        f'td:has-text("{term.replace(chr(34), chr(92) + chr(34))}") + td'
        for term in get_localized_terms(profile.language, category)
    ]


def _caption_matches(caption, profile, vehicle_types):
    caption_key = _normalize(caption)
    aliases = profile.vehicle_aliases()
    names = []
    for vehicle_type in vehicle_types:
        names.extend(profile.vehicle_options(vehicle_type))
        names.extend(aliases.get(vehicle_type, []))
    return any(_normalize(name) in caption_key for name in names if _normalize(name))


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
                                "name": normalize_name(match.group(2), profile.language),
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
                    if not await handle_prisoner_transport(page, profile):
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
                        transported = sum(
                            1
                            for caption in result["captions"]
                            if _caption_matches(
                                caption,
                                profile,
                                ("police car", "patrol car", "prisoner transport van"),
                            )
                            or any(
                                marker in _normalize(caption)
                                for marker in (
                                    "patrol car",
                                    "supervisor",
                                    "sheriff",
                                    "police car",
                                )
                            )
                        )
                        remaining = max(0, result["prisoners"] - transported)
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
            credits = await get_val(page, _value_selectors(profile, "average_credits"), True)
            patients = await get_val(page, _value_selectors(profile, "max_patients"))
            crashed = await get_val(page, _value_selectors(profile, "towed_cars"))
            if patients:
                requirements["vehicles"].append({"name": "ambulance", "count": patients})
                if patients >= 10:
                    requirements["vehicles"].append({"name": "ems chief", "count": 1})
                if patients >= 20:
                    requirements["vehicles"].append(
                        {"name": "ems mobile command unit", "count": 1}
                    )

            vehicles, liquid = [], []
            for vehicle in (*requirements["vehicles"], *requirements["liquid"]):
                entry = resolve_vehicle_entry(vehicle["name"], vehicle["count"], profile)
                if any(
                    _normalize(option) in {"water", "foam", "schaum", "espuma", "schuim"}
                    for option in entry["options"]
                ):
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
