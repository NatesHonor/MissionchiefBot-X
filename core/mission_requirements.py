"""Mission requirement parsing parameterized by region data."""

from __future__ import annotations

import json
import re
import unicodedata

from .mission_helpers import normalize_name
from .localization import contains_localized_term, get_localized_terms
from .regions import get_region_profile


def _load_json(path):
    try:
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(character for character in value if not unicodedata.combining(character))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]+", " ", value.casefold())).strip()


def resolve_personnel(name: str, profile=None) -> str:
    profile = profile or get_region_profile()
    normalized = _normalize(name)
    aliases = profile.personnel_aliases()
    for canonical, synonyms in aliases.items():
        if normalized in {_normalize(canonical), *(_normalize(synonym) for synonym in synonyms)}:
            return canonical
    return name


async def gather_requirements(page, profile=None):
    profile = profile or get_region_profile()
    requirement_map = {
        _normalize(key): value for key, value in profile.requirement_mapping().items()
    }
    requirements = {"vehicles": [], "personnel": [], "liquid": []}

    table = await page.query_selector(
        'div.col-md-4 > table:has(th:has-text("Vehicle and Personnel Requirements"))'
    )
    if not table:
        tables = await page.query_selector_all("div.col-md-4 > table")
        for candidate in tables:
            if contains_localized_term(
                await candidate.inner_text(), profile.language, "required"
            ):
                table = candidate
                break
    if table:
        for row in await table.query_selector_all("tr:has(td)"):
            if not contains_localized_term(
                await row.inner_text(), profile.language, "required"
            ):
                continue
            name_element = await row.query_selector("td:first-child")
            count_element = await row.query_selector("td:nth-child(2)")
            if not name_element or not count_element:
                continue
            raw_name = await name_element.text_content()
            name = normalize_name(raw_name or "", profile.language)
            if "probability" in _normalize(name):
                continue
            count_text = (await count_element.text_content()).strip().lower()
            try:
                count = int(count_text)
            except (TypeError, ValueError):
                count = count_text
            kind = requirement_map.get(_normalize(name), "vehicles")
            entry = {"name": name, "count": count}
            if kind == "liquid":
                requirements["liquid"].append(entry)
            elif kind not in {"pass", "info", "tow_vehicle"}:
                requirements["vehicles"].append({"name": name, "count": count})

    table = await page.query_selector(
        'div.col-md-4 > table:has(th:has-text("Other information"))'
    )
    if not table:
        tables = await page.query_selector_all("div.col-md-4 > table")
        for candidate in tables:
            candidate_text = await candidate.inner_text()
            if contains_localized_term(
                candidate_text, profile.language, "other_information"
            ) or (
                contains_localized_term(candidate_text, profile.language, "personnel")
                and not contains_localized_term(candidate_text, profile.language, "required")
            ):
                table = candidate
                break
    if table:
        for row in await table.query_selector_all("tr"):
            header_element = await row.query_selector("td:first-child")
            value_element = await row.query_selector("td:nth-child(2)")
            if not header_element or not value_element:
                continue
            header = await header_element.inner_text()
            if not contains_localized_term(header, profile.language, "personnel"):
                continue
            html = await value_element.inner_html()
            text = re.sub(r"<br\s*/?>", "\n", html)
            text = re.sub(r"<[^>]+>", "", text)
            for entry in re.split(r"[,\n]+", text.replace("\xa0", " ")):
                match = re.match(r"(\d+)\s*x?\s*(.+)", entry.strip())
                if match:
                    count, raw_name = int(match.group(1)), normalize_name(
                        match.group(2), profile.language
                    )
                    requirements["personnel"].append(
                        {
                            "name": resolve_personnel(raw_name, profile),
                            "count": count,
                        }
                    )

    for person in requirements["personnel"]:
        if _normalize(person["name"]) != "swat personnel":
            continue
        divisions = person["count"] // 6
        if divisions <= 0:
            continue
        for vehicle in requirements["vehicles"]:
            if "swat armoured vehicle" in _normalize(vehicle["name"]):
                vehicle["count"] = max(0, vehicle["count"] - divisions)
        requirements["vehicles"] = [
            vehicle
            for vehicle in requirements["vehicles"]
            if not (
                _normalize(vehicle["name"]).startswith("swat armoured vehicle")
                and vehicle["count"] == 0
            )
        ]

    return requirements
