from __future__ import annotations

import asyncio
import re

from utils.pretty_print import display_error, display_info

from ..regions import get_region_profile
from ..vehicle_state import get_vehicle_state
from ..vehicle_mapping import is_decorated_vehicle_name, vehicle_name_variants
from .utils import format_distance, normalize_key


async def get_all_vehicle_distances(page, ids):
    script = r"""
    (ids) => {
        const parseDistance = (value) => {
            const text = String(value || '').trim().toLowerCase();
            if (!text) return Infinity;
            const clock = text.match(/^(?:(\d+)\s*:\s*)?(\d+)\s*:\s*(\d+)$/);
            if (clock) {
                return (Number(clock[1] || 0) * 3600) +
                    (Number(clock[2]) * 60) + Number(clock[3]);
            }
            const hours = text.match(/(\d+(?:[.,]\d+)?)\s*(?:h|hr|hour|hours)/);
            const minutes = text.match(/(\d+(?:[.,]\d+)?)\s*(?:m|min|minute|minutes)/);
            const seconds = text.match(/(\d+(?:[.,]\d+)?)\s*(?:s|sec|second|seconds)/);
            if (hours || minutes || seconds) {
                return (Number((hours?.[1] || '0').replace(',', '.')) * 3600) +
                    (Number((minutes?.[1] || '0').replace(',', '.')) * 60) +
                    Number((seconds?.[1] || '0').replace(',', '.'));
            }
            const number = text.match(/\d+(?:[.,]\d+)?/);
            return number ? Number(number[0].replace(',', '.')) : Infinity;
        };
        const result = {};
        for (const id of ids) {
            const checkbox = document.querySelector(`input.vehicle_checkbox[value="${id}"]`);
            const row = checkbox?.closest('tr, li, [data-vehicle-id]');
            const elements = [
                document.querySelector(`#vehicle_sort_${id}`),
                checkbox,
                row,
                document.querySelector(`[data-vehicle-id="${id}"]`),
            ].filter(Boolean);
            const values = elements.flatMap((element) => [
                element.getAttribute('sortvalue'),
                element.getAttribute('data-sortvalue'),
                element.getAttribute('data-distance'),
                element.getAttribute('distance'),
            ]).filter(Boolean);
            let distance = Infinity;
            for (const value of values) {
                distance = parseDistance(value);
                if (Number.isFinite(distance)) break;
            }
            if (!Number.isFinite(distance) && row) {
                const rowText = row.innerText || '';
                if (/(?:\\d+\\s*(?:h|hr|hour|hours|m|min|minute|minutes|s|sec|second|seconds)|\\d+\\s*:\s*\\d+)/i.test(rowText)) {
                    distance = parseDistance(rowText);
                }
            }
            result[id] = distance;
        }
        return result;
    }
    """
    return await page.evaluate(script, ids)


def parse_distance_value(value) -> float:
    """Normalize numeric and localized duration values for stable sorting."""

    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip().casefold()
    if not text:
        return float("inf")
    clock = re.fullmatch(r"(?:(\d+)\s*:\s*)?(\d+)\s*:\s*(\d+)", text)
    if clock:
        return int(clock.group(1) or 0) * 3600 + int(clock.group(2)) * 60 + int(clock.group(3))

    def amount(pattern):
        match = re.search(pattern, text)
        return float(match.group(1).replace(",", ".")) if match else 0.0

    if re.search(r"\d+(?:[.,]\d+)?\s*(?:h|hr|hour|hours|m|min|minute|minutes|s|sec|second|seconds)", text):
        return (
            amount(r"(\d+(?:[.,]\d+)?)\s*(?:h|hr|hour|hours)") * 3600
            + amount(r"(\d+(?:[.,]\d+)?)\s*(?:m|min|minute|minutes)") * 60
            + amount(r"(\d+(?:[.,]\d+)?)\s*(?:s|sec|second|seconds)")
        )
    match = re.search(r"\d+(?:[.,]\d+)?", text)
    return float(match.group(0).replace(",", ".")) if match else float("inf")


async def click_vehicle(page, checkbox, vehicle_id, label, distance, mission_id, state=None, profile=None):
    state = state or get_vehicle_state(profile or get_region_profile())
    if await checkbox.is_checked() or not state.lock(str(vehicle_id), str(mission_id)):
        return False
    try:
        await page.evaluate(
            "(c) => { c.click(); c.dispatchEvent(new Event('change', { bubbles: true })); }",
            checkbox,
        )
    except Exception:
        state.unlock(str(vehicle_id), str(mission_id))
        return False
    display_info(f"Selected {label}({vehicle_id}) [{format_distance(distance)} away]")
    return True


async def select_vehicles(
    page,
    ids,
    needed,
    label,
    mission_id,
    profile=None,
    state=None,
):
    state = state or get_vehicle_state(profile or get_region_profile())
    if needed <= 0:
        return 0
    checkbox_map = {}
    valid_ids = []
    for attempt in range(3):
        checkboxes = await page.query_selector_all("input.vehicle_checkbox")
        checkbox_map = {
            await checkbox.get_attribute("value"): checkbox for checkbox in checkboxes
        }
        valid_ids = [
            vehicle_id
            for vehicle_id in ids
            if vehicle_id in checkbox_map and not state.is_locked(vehicle_id)
        ]
        if valid_ids:
            break
        if attempt < 2:
            try:
                await page.wait_for_selector("input.vehicle_checkbox", timeout=1500)
            except Exception:
                pass
            await asyncio.sleep(0.25 * (attempt + 1))
    if not valid_ids:
        return 0
    distance_map = await get_all_vehicle_distances(page, valid_ids)
    vehicles = [
        (vehicle_id, parse_distance_value(distance_map.get(vehicle_id, float("inf"))))
        for vehicle_id in valid_ids
    ]
    vehicles.sort(key=lambda item: item[1])
    selected = 0
    for vehicle_id, distance in vehicles:
        if selected >= needed:
            break
        if await click_vehicle(
            page,
            checkbox_map[vehicle_id],
            vehicle_id,
            label,
            distance,
            mission_id,
            state,
            profile,
        ):
            selected += 1
    return selected


async def find_vehicle_ids(name: str, profile=None, state=None, exact=False, quiet=False):
    profile = profile or get_region_profile()
    state = state or get_vehicle_state(profile)
    vehicle_data = state.get_data()
    ids = []
    names = [name]
    if not exact:
        names.extend(profile.vehicle_options(name))
    normalized_names = {
        variant
        for item in names
        if item
        for variant in vehicle_name_variants(item)
    }
    for vehicle_type, vehicle_ids in vehicle_data.items():
        normalized_type = normalize_key(vehicle_type)
        matches_name = bool(normalized_names & vehicle_name_variants(vehicle_type))
        # Inventory captions sometimes append a model/crew qualifier in
        # parentheses.  Permit that explicit decoration, but do not fall
        # back to arbitrary substring matches between unrelated vehicle types.
        decorated_match = (not exact) and is_decorated_vehicle_name(
            normalized_names, vehicle_type
        )
        if matches_name or decorated_match:
            ids.extend(str(vehicle_id) for vehicle_id in vehicle_ids)
    unique_ids = list(dict.fromkeys(ids))
    if not unique_ids and not quiet:
        display_error(f"No vehicles found for '{name}'")
    return unique_ids
