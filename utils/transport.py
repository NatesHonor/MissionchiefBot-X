"""Transport request handling with API-first vehicle and destination lookup."""

from __future__ import annotations

import re
import unicodedata

from core.localization import contains_localized_term
from core.missionchief_api import fetch_vehicle_records
from core.pages import ensure_page
from core.regions import get_region_profile
from utils.pretty_print import display_error, display_info


_DEPARTMENT_MARKERS = (
    "department",
    "specialization",
    "speciality",
    "abteilung",
    "fachabteilung",
    "departamento",
    "especialidade",
    "avdelning",
    "specialitet",
    "afdeling",
    "specialisatie",
    "specialiteit",
    "dienst",
)
_TAX_LABELS = ("tax", "imposto", "skatt", "steuer", "belasting")
_DISTANCE_LABELS = ("distance", "distancia", "avstand", "entfernung", "afstand")
_OWN_MARKERS = ("own", "owned", "eigen", "meu", "min", "egen", "propri", "mijn", "eigendom")
_PATIENT_MARKERS = (
    "patient",
    "patients",
    "patiënt",
    "patiënten",
    "patienten",
    "patienter",
    "paciente",
    "pacientes",
    "paziente",
    "pazienti",
    "pacjent",
    "pacjentów",
)


async def _button_label(button) -> str:
    """Return a useful action label even when the button only has an ARIA title."""

    text = (await button.inner_text()).strip()
    if text:
        return text
    for attribute in ("aria-label", "title", "data-original-title"):
        value = (await button.get_attribute(attribute) or "").strip()
        if value:
            return value
    return ""


def _display_metric(value) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "unknown"
    if number == float("inf"):
        return "unknown"
    return str(int(number)) if number.is_integer() else f"{number:g}"


def _contains_word_marker(value: str, markers: tuple[str, ...]) -> bool:
    value = _fold(value)
    return any(
        re.search(rf"(?<![a-z]){re.escape(marker)}(?![a-z])", value)
        for marker in markers
    )


def _fold(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(character for character in value if not unicodedata.combining(character)).casefold()


def _number(value: str | None) -> float:
    match = re.search(r"\d+(?:[.,]\d+)?", str(value or ""))
    if not match:
        return float("inf")
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return float("inf")


def _labeled_number(text: str, labels: tuple[str, ...]) -> float:
    label_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(
        rf"(?:{label_pattern})\s*:?\s*(\d+(?:[.,]\d+)?)",
        text,
        flags=re.IGNORECASE,
    )
    return _number(match.group(1)) if match else float("inf")


def transport_option_key(option: dict) -> tuple[float, float, float, float]:
    """Sort department, ownership, tax, and distance in that priority order."""

    return (
        -float(bool(option.get("has_department"))),
        -float(bool(option.get("own"))),
        float(option.get("tax", float("inf"))),
        float(option.get("distance", float("inf"))),
    )


def is_transport_request(record: dict) -> bool:
    """Recognize transport flags returned by different MissionChief APIs."""

    if not isinstance(record, dict):
        return False
    values = [
        record.get(key)
        for key in (
            "fms_real",
            "fms",
            "fmsReal",
            "transport_type",
            "transportType",
            "transport_status",
        )
    ]
    if any(
        str(value).strip().casefold()
        in {"5", "true", "transport", "transport_requested", "patient_transport"}
        for value in values
    ):
        return True
    return any(
        str(record.get(key, "")).strip().casefold() in {"1", "true", "yes", "transport"}
        for key in ("needs_transport", "transport_requested", "transport")
    )


def is_patient_transport_option(option: dict, profile=None) -> bool:
    """Identify hospital actions that explicitly transport a patient."""

    if not isinstance(option, dict):
        return False
    label = str(option.get("action_label") or option.get("label") or "")
    if any(marker in _fold(label) for marker in _PATIENT_MARKERS):
        return True
    if profile is not None and contains_localized_term(
        label, profile.language, "patient_transport"
    ):
        return True
    return False


def choose_transport_option(options: list[dict], profile=None) -> dict | None:
    """Prefer explicit patient actions, then apply the normal destination priority."""

    if not options:
        return None
    patient_options = [
        option for option in options if is_patient_transport_option(option, profile)
    ]
    return min(patient_options or options, key=transport_option_key)


async def _row_metadata(row) -> dict:
    return await row.evaluate(
        """
        (element) => {
            const table = element.closest('table');
            const values = (node) => node ? {
                id: node.id || '',
                className: node.className || '',
                text: node.innerText || '',
            } : {id: '', className: '', text: ''};
            return {
                row: values(element),
                table: values(table),
            };
        }
        """
    )


async def _transport_options(page) -> list[dict]:
    rows = await page.query_selector_all(
        "table#own-hospitals tbody tr, table[id*='hospital'] tbody tr, "
        "table[id*='prison'] tbody tr, table[id*='transport'] tbody tr"
    )
    if not rows:
        rows = await page.query_selector_all("table tbody tr")

    options = []
    for row in rows:
        button = await row.query_selector(
            "a.btn.btn-success, button.btn.btn-success, a.btn-success, button.btn-success"
        )
        if not button:
            continue
        metadata = await _row_metadata(row)
        row_data = metadata.get("row", {})
        table_data = metadata.get("table", {})
        text = " ".join(
            str(value or "")
            for value in (row_data.get("text"), table_data.get("id"), table_data.get("className"))
        )
        lower_text = _fold(text)
        ownership_text = " ".join(
            str(value or "")
            for value in (
                row_data.get("id"),
                row_data.get("className"),
                table_data.get("id"),
                table_data.get("className"),
            )
        ).casefold()
        distance = _labeled_number(text, _DISTANCE_LABELS)
        tax = _labeled_number(text, _TAX_LABELS)
        if tax == float("inf"):
            percentage = re.search(r"\d+(?:[.,]\d+)?\s*%", text)
            tax = _number(percentage.group(0)) if percentage else float("inf")
        if distance == float("inf"):
            cells = await row.query_selector_all("td")
            if len(cells) >= 2:
                distance = _number(await cells[1].inner_text())
        action_label = await _button_label(button)
        if not row_data.get("text", "").strip() and not action_label:
            # Do not click icon-only or unrelated success buttons.  The old
            # fallback treated those as destinations and produced blank
            # transport records.
            continue
        options.append(
            {
                "button": button,
                "label": (row_data.get("text") or "").strip(),
                "action_label": action_label,
                "has_department": any(marker in lower_text for marker in _DEPARTMENT_MARKERS),
                "own": _contains_word_marker(ownership_text, _OWN_MARKERS),
                "tax": tax,
                "distance": distance,
            }
        )

    if options:
        return options

    # Keep compatibility with deployments that render destination buttons
    # outside a table, while still applying the same sorting rules.
    for button in await page.query_selector_all("a.btn.btn-success, button.btn.btn-success"):
        text = await _button_label(button)
        if not text:
            continue
        options.append(
            {
                "button": button,
                "label": text,
                "action_label": text,
                "has_department": any(marker in _fold(text) for marker in _DEPARTMENT_MARKERS),
                "own": False,
                "tax": _labeled_number(text, _TAX_LABELS),
                "distance": _labeled_number(text, _DISTANCE_LABELS),
            }
        )
    return options


async def _release_without_transport(page) -> bool:
    release = await page.query_selector(
        "#leave_without_transport_no_compensation, "
        "a.btn.btn-xs.btn-danger, button.btn.btn-xs.btn-danger, a.btn-danger"
    )
    if not release:
        return False
    await release.click()
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=5000)
    except Exception:
        pass
    return True


async def _fallback_transport_vehicle_ids(page, profile) -> list[str]:
    prisoner_alerts = await page.query_selector_all("div.alert.alert-danger")
    prisoner_missions = set()
    for alert in prisoner_alerts:
        text = (await alert.inner_text()).strip()
        if contains_localized_term(text, profile.language, "prisoner_transport"):
            mission_id = await alert.get_attribute("id")
            if mission_id and mission_id.startswith("mission_missing_"):
                prisoner_missions.add(mission_id.replace("mission_missing_", ""))
    if prisoner_missions:
        display_info(f"Prisoner transport missions: {', '.join(prisoner_missions)}")

    transport_requests = await page.query_selector_all("ul#radio_messages_important li")
    vehicle_ids = []
    for request in transport_requests:
        vehicle_id = await request.get_attribute("vehicle_id")
        if not vehicle_id:
            vehicle_id = await request.get_attribute("data-vehicle-id")
        if not vehicle_id:
            image = await request.query_selector("img")
            if image:
                vehicle_id = await image.get_attribute("vehicle_id")
        if not vehicle_id:
            link = await request.query_selector("a[href*='/vehicles/']")
            href = await link.get_attribute("href") if link else ""
            match = re.search(r"/vehicles/(\d+)", href or "")
            vehicle_id = match.group(1) if match else None
        if vehicle_id:
            vehicle_ids.append(str(vehicle_id))
    return list(dict.fromkeys(vehicle_ids))


async def handle_transport_requests(context, url, profile=None):
    profile = profile or get_region_profile()
    page = await ensure_page(context)
    await page.goto(url, wait_until="domcontentloaded")

    records = await fetch_vehicle_records(page, url)
    vehicle_ids = [
        str(record["id"])
        for record in records
        if record.get("id") is not None and is_transport_request(record)
    ]
    if not vehicle_ids:
        vehicle_ids = await _fallback_transport_vehicle_ids(page, profile)
    vehicle_ids = list(dict.fromkeys(vehicle_ids))
    display_info(f"Found {len(vehicle_ids)} transport requests")

    for vehicle_id in vehicle_ids:
        vehicle_url = f"{url.rstrip('/')}/vehicles/{vehicle_id}"
        try:
            await page.goto(vehicle_url, wait_until="domcontentloaded")
            options = await _transport_options(page)
            if options:
                chosen = choose_transport_option(options, profile)
                if chosen is None:
                    raise RuntimeError("transport destination list was empty")
                await chosen["button"].click()
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=5000)
                except Exception:
                    pass
                display_info(
                    f"Transported vehicle {vehicle_id} to '{chosen['label']}' "
                    f"(tax {_display_metric(chosen['tax'])}, "
                    f"distance {_display_metric(chosen['distance'])})."
                )
            elif await _release_without_transport(page):
                display_info(f"Released vehicle {vehicle_id} because no transport was available")
            else:
                display_error(f"No transport or release option found for vehicle {vehicle_id}")
        except Exception as error:
            display_error(
                f"Transport handling failed for {vehicle_url}: "
                f"{type(error).__name__}: {error or 'unknown error'}"
            )

    await page.goto(url, wait_until="domcontentloaded")
    display_info("Finished handling all transport requests and returned to the main map")
