"""Session-authenticated MissionChief API helpers with safe fallbacks."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path


async def _fetch(page, base_url: str, endpoint: str, accept: str):
    return await page.evaluate(
        """
        async ({baseUrl, endpoint, accept}) => {
            const response = await fetch(new URL(endpoint, baseUrl), {
                credentials: 'include',
                headers: { Accept: accept },
            });
            if (!response.ok) {
                return null;
            }
            return await response.text();
        }
        """,
        {"baseUrl": base_url, "endpoint": endpoint, "accept": accept},
    )


async def fetch_json(page, base_url: str, endpoints: list[str]):
    """Return the first valid JSON response from the supplied endpoints."""

    for endpoint in endpoints:
        try:
            content = await _fetch(page, base_url, endpoint, "application/json")
            if not content:
                continue
            return json.loads(content)
        except Exception:
            continue
    return None


async def fetch_text(page, base_url: str, endpoints: list[str]) -> str | None:
    """Return the first non-empty text response from the supplied endpoints."""

    for endpoint in endpoints:
        try:
            content = await _fetch(page, base_url, endpoint, "text/javascript, application/json")
            if content:
                return content
        except Exception:
            continue
    return None


def records_from_payload(payload) -> list[dict]:
    """Normalize common MissionChief API collection shapes into records."""

    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("result", "results", "vehicles", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            records = []
            for record_id, item in value.items():
                if isinstance(item, dict):
                    record = dict(item)
                    record.setdefault("id", record_id)
                    records.append(record)
            if records:
                return records
    return []


def vehicle_inventory_from_records(records: list[dict]) -> dict[str, list[str]]:
    """Group API vehicles by useful localized captions while preserving IDs."""

    inventory: dict[str, list[str]] = {}
    for vehicle in records:
        vehicle_id = vehicle.get("id")
        if vehicle_id is None:
            continue
        labels = [
            vehicle.get("vehicle_type_caption"),
            vehicle.get("caption"),
            str(vehicle.get("vehicle_type")) if vehicle.get("vehicle_type") is not None else None,
        ]
        label = next((str(value).strip() for value in labels if str(value or "").strip()), None)
        if not label:
            continue
        inventory.setdefault(label, []).append(str(vehicle_id))
    return inventory


async def fetch_vehicle_records(page, base_url: str) -> list[dict]:
    """Fetch the paged v2 vehicle API, falling back to the legacy endpoint."""

    for endpoint in ("/api/v2/vehicles", "/api/vehicles"):
        records: list[dict] = []
        first = await fetch_json(page, base_url, [endpoint])
        first_records = records_from_payload(first)
        if not first_records:
            continue
        records.extend(first_records)
        paging = first.get("paging", {}) if isinstance(first, dict) else {}
        total_pages = paging.get("pages") or paging.get("total_pages")
        next_page = paging.get("next_page")
        if isinstance(next_page, int):
            total_pages = max(int(total_pages or 1), next_page)
        if isinstance(total_pages, str) and total_pages.isdigit():
            total_pages = int(total_pages)
        if not isinstance(total_pages, int) or total_pages <= 1:
            return records
        for page_number in range(2, min(total_pages, 100) + 1):
            separator = "&" if "?" in endpoint else "?"
            payload = await fetch_json(
                page,
                base_url,
                [f"{endpoint}{separator}page={page_number}"],
            )
            page_records = records_from_payload(payload)
            if not page_records:
                break
            records.extend(page_records)
        return records
    return []


async def fetch_mission_index(page, base_url: str):
    """Fetch the one-request mission type index exposed by MissionChief."""

    payload = await fetch_json(page, base_url, ["/einsaetze.json"])
    return payload if isinstance(payload, (dict, list)) else None


def extract_mission_ids(value) -> list[str]:
    """Extract active mission IDs from marker JSON or JavaScript responses."""

    if isinstance(value, (dict, list)):
        encoded = json.dumps(value, ensure_ascii=False)
    else:
        encoded = str(value or "")
    pattern = (
        r"(?<![A-Za-z_])[\"']?(?:mission[_-]?id|missionId|id)[\"']?"
        r"\s*[:=]\s*[\"']?(\d+)"
    )
    ids = re.findall(pattern, encoded, flags=re.IGNORECASE)
    return list(dict.fromkeys(ids))


def extract_mission_marker_records(value) -> list[dict]:
    """Extract active mission IDs and optional mission-type IDs from markers."""

    if isinstance(value, (dict, list)):
        records = []
        values = value if isinstance(value, list) else [value]
        for item in values:
            if not isinstance(item, dict):
                continue
            mission_id = next(
                (item.get(key) for key in ("mission_id", "missionId", "id") if item.get(key) is not None),
                None,
            )
            if mission_id is None:
                continue
            type_id = next(
                (
                    item.get(key)
                    for key in ("mtid", "mission_type_id", "missionTypeId", "mission_type")
                    if item.get(key) is not None
                ),
                None,
            )
            records.append({"id": str(mission_id), "type_id": str(type_id) if type_id is not None else None, "name": item.get("name") or item.get("mission_name")})
        return list({record["id"]: record for record in records}.values())

    text = str(value or "")
    records = []
    id_pattern = re.compile(
        r"(?<![A-Za-z_])(?:[\"']?(?:mission[_-]?id|missionId|id)[\"']?)\s*[:=]\s*[\"']?(\d+)",
        re.IGNORECASE,
    )
    type_pattern = re.compile(
        r"(?:[\"']?(?:mtid|mission[_-]?type[_-]?id|missionTypeId)[\"']?)\s*[:=]\s*[\"']?(\d+)",
        re.IGNORECASE,
    )
    for match in id_pattern.finditer(text):
        start = max(0, text.rfind("{", 0, match.start()))
        end = text.find("}", match.end())
        segment = text[start : end if end >= 0 else min(len(text), match.end() + 400)]
        type_match = type_pattern.search(segment)
        records.append(
            {
                "id": match.group(1),
                "type_id": type_match.group(1) if type_match else None,
                "name": None,
            }
        )
    return list({record["id"]: record for record in records}.values())


async def fetch_mission_markers(page, base_url: str) -> list[str]:
    """Fetch own and alliance marker endpoints and combine their mission IDs."""

    ids = []
    for endpoint in (
        "/map/mission_markers_own.js.erb",
        "/map/mission_markers_alliance.js.erb",
    ):
        content = await fetch_text(page, base_url, [endpoint])
        ids.extend(extract_mission_ids(content))
    return list(dict.fromkeys(ids))


async def fetch_mission_marker_records(page, base_url: str) -> list[dict]:
    """Fetch marker metadata needed to match ignore rules by mission type."""

    records = []
    for endpoint in (
        "/map/mission_markers_own.js.erb",
        "/map/mission_markers_alliance.js.erb",
    ):
        content = await fetch_text(page, base_url, [endpoint])
        records.extend(extract_mission_marker_records(content))
    return list({record["id"]: record for record in records}.values())


async def refresh_mission_index(page, base_url: str, destination: Path, max_age: int = 86400):
    """Refresh a local mission index at most once per day and return its data."""

    try:
        if destination.exists() and time.time() - destination.stat().st_mtime < max_age:
            return json.loads(destination.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    payload = await fetch_mission_index(page, base_url)
    if payload is None:
        return None
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass
    return payload
