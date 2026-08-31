import re

from .localization import get_localized_terms
from .regions import get_region_profile


async def handle_prisoner_transport(page, profile=None):
    profile = profile or get_region_profile()
    try:
        while True:
            buttons = []
            for division in await page.query_selector_all("div.prison-select"):
                for button in await division.query_selector_all("a.btn-success, a.btn-warning"):
                    buttons.append((await extract_distance(button, profile), button))
            if not buttons:
                return False
            await sorted(buttons, key=lambda item: item[0])[0][1].click()
            await page.wait_for_load_state("networkidle")
    except Exception:
        return False


async def extract_distance(button, profile=None):
    profile = profile or get_region_profile()
    try:
        text = await button.inner_text()
        labels = get_localized_terms(profile.language, "distance")
        label_pattern = "|".join(re.escape(label) for label in labels)
        match = re.search(
            rf"(?:{label_pattern})\s*[:\-]?\s*([\d.,]+)\s*(?:km|公里)?",
            text,
            re.IGNORECASE,
        )
        if not match:
            return float("inf")
        raw_value = match.group(1)
        if "." in raw_value and "," in raw_value:
            raw_value = raw_value.replace(".", "").replace(",", ".")
        elif "," in raw_value:
            raw_value = raw_value.replace(",", ".")
        elif raw_value.count(".") > 1:
            raw_value = raw_value.replace(".", "")
        return float(raw_value)
    except (AttributeError, TypeError, ValueError):
        return float("inf")
