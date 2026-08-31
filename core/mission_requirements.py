"""Mission requirement parsing parameterized by region data."""

from __future__ import annotations

import json
import re

from .mission_helpers import normalize_name
from .regions import get_region_profile


def _load_json(path):
    try:
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def resolve_personnel(name: str, profile=None) -> str:
    profile = profile or get_region_profile()
    normalized = name.lower()
    aliases = _load_json(profile.personnel_aliases_file)
    for canonical, synonyms in aliases.items():
        if normalized == canonical.lower() or normalized in [synonym.lower() for synonym in synonyms]:
            return canonical
    return name


async def gather_requirements(page, profile=None):
    profile = profile or get_region_profile()
    requirement_map = _load_json(profile.requirement_mapping_file)
    requirements = {"vehicles": [], "personnel": [], "liquid": []}

    table = await page.query_selector(
        'div.col-md-4 > table:has(th:has-text("Vehicle and Personnel Requirements"))'
    )
    if table:
        for row in await table.query_selector_all('tr:has(td:has-text("Required"))'):
            name_element = await row.query_selector("td:first-child")
            count_element = await row.query_selector("td:nth-child(2)")
            if not name_element or not count_element:
                continue
            raw_name = await name_element.text_content()
            name = normalize_name(raw_name or "")
            if "probability" in name:
                continue
            count_text = (await count_element.text_content()).strip().lower()
            try:
                count = int(count_text)
            except (TypeError, ValueError):
                count = count_text
            if requirement_map.get(name, "vehicles") == "vehicles":
                requirements["vehicles"].append({"name": name, "count": count})

    table = await page.query_selector(
        'div.col-md-4 > table:has(th:has-text("Other information"))'
    )
    if table:
        for row in await table.query_selector_all("tr"):
            header_element = await row.query_selector("td:first-child")
            value_element = await row.query_selector("td:nth-child(2)")
            if not header_element or not value_element:
                continue
            header = (await header_element.inner_text()).lower()
            if "required personnel" not in header:
                continue
            html = await value_element.inner_html()
            text = re.sub(r"<br\s*/?>", "\n", html)
            text = re.sub(r"<[^>]+>", "", text)
            for entry in re.split(r"[,\n]+", text.replace("\xa0", " ")):
                match = re.match(r"(\d+)\s*x?\s*(.+)", entry.strip())
                if match:
                    count, raw_name = int(match.group(1)), normalize_name(match.group(2))
                    requirements["personnel"].append(
                        {
                            "name": resolve_personnel(raw_name, profile),
                            "count": count,
                        }
                    )

    for person in requirements["personnel"]:
        if person["name"].lower() != "swat personnel":
            continue
        divisions = person["count"] // 6
        if divisions <= 0:
            continue
        for vehicle in requirements["vehicles"]:
            if "swat armoured vehicle" in vehicle["name"].lower():
                vehicle["count"] = max(0, vehicle["count"] - divisions)
        requirements["vehicles"] = [
            vehicle
            for vehicle in requirements["vehicles"]
            if not (
                vehicle["name"].lower().startswith("swat armoured vehicle")
                and vehicle["count"] == 0
            )
        ]

    return requirements
