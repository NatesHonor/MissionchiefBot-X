"""Automatic station recruitment through MissionChief's desired-staff control."""

from __future__ import annotations

import re
import unicodedata

from utils.pretty_print import display_error, display_info


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]+", " ", value.casefold())).strip()


def _integer_from(value: str, default: int = 0) -> int:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group()) if match else default


def desired_recruitment_target(current: int, desired: int, days: int) -> int:
    """Keep an existing higher target while ensuring ``days`` of hiring remain."""

    return max(current + max(1, days), desired)


async def _facility_links(page, base_url: str) -> list[str]:
    await page.goto(f"{base_url.rstrip('/')}/buildings", wait_until="domcontentloaded")
    links = []
    seen = set()
    for link in await page.query_selector_all("a[href*='/buildings/']"):
        href = await link.get_attribute("href")
        if not href:
            continue
        url = href if href.startswith("http") else f"{base_url.rstrip('/')}/{href.lstrip('/')}"
        if url not in seen:
            seen.add(url)
            links.append(url)
    return links


async def recruit_at_facility(page, facility_url: str, days: int) -> dict[str, int | str]:
    await page.goto(facility_url, wait_until="domcontentloaded")
    forms = await page.query_selector_all("form")
    for form in forms:
        form_text = _normalize(await form.inner_text())
        inputs = await form.query_selector_all(
            "input[name*='personnel'], input[id*='personnel'], input[name*='staff'], input[id*='staff']"
        )
        if not inputs or not any(
            marker in form_text
            for marker in ("personnel", "staff", "desired", "automatically", "recruit")
        ):
            continue
        target_input = inputs[0]
        current = _integer_from(
            await target_input.evaluate(
                "element => element.closest('tr, .form-group, .panel')?.innerText || ''"
            )
        )
        desired = _integer_from(await target_input.get_attribute("value"))
        target = desired_recruitment_target(current, desired, days)
        if desired >= target:
            return {"facility": facility_url, "updated": 0, "target": desired}

        await target_input.fill(str(target))
        buttons = await form.query_selector_all(
            "button, input[type='submit'], a.btn"
        )
        for button in buttons:
            label = _normalize(
                f"{await button.inner_text()} {await button.get_attribute('value') or ''} "
                f"{await button.get_attribute('name') or ''}"
            )
            if not any(
                marker in label
                for marker in ("automatically", "auto recruit", "automatisch", "automatica", "recruit")
            ):
                continue
            await button.click()
            await page.wait_for_load_state("networkidle")
            return {"facility": facility_url, "updated": 1, "target": target}
        display_error(f"Recruitment button not found at {facility_url}")
        return {"facility": facility_url, "updated": 0, "target": desired}
    return {"facility": facility_url, "updated": 0, "target": 0}


async def run_recruiting_once(context, base_url: str, days: int) -> list[dict[str, int | str]]:
    page = context.pages[0] if context.pages else await context.new_page()
    results = []
    try:
        facilities = await _facility_links(page, base_url)
        for facility_url in facilities:
            try:
                result = await recruit_at_facility(page, facility_url, days)
                if result["updated"]:
                    display_info(f"Started automatic recruitment at {facility_url}.")
                results.append(result)
            except Exception as error:
                display_error(f"Recruitment error at {facility_url}: {error}")
        return results
    except Exception as error:
        display_error(f"Could not scan facilities for recruitment: {error}")
        return results
