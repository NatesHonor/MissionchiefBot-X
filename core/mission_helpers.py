"""Pure helpers used while reading mission pages."""

import re

from .localization import get_localized_terms


async def get_val(page, selector, split_first=False):
    selectors = [selector] if isinstance(selector, str) else selector
    for candidate in selectors:
        element = await page.query_selector(candidate)
        if not element:
            continue
        text = (await element.inner_text()).strip()
        numbers = re.findall(r"\d[\d\s.,]*", text)
        if not numbers:
            continue
        value = numbers[0] if split_first else numbers[-1]
        try:
            # MissionChief uses both comma and dot thousands separators across
            # regional pages; counts are integers, so discard both safely.
            return int(re.sub(r"[^0-9]", "", value))
        except (TypeError, ValueError):
            continue
    return 0


def normalize_name(raw, language="en"):
    """Normalize a localized requirement name without destroying vehicle words."""

    name = re.sub(r"\s+", " ", str(raw or "").replace("\xa0", " ").strip()).casefold()
    prefixes = set(get_localized_terms(language, "required"))
    prefixes.update({"vehicle", "vehicles", "car", "cars"})
    for prefix in sorted(prefixes, key=len, reverse=True):
        name = re.sub(rf"^(?:{re.escape(prefix)})\s+", "", name).strip()
    return remove_plural_suffix(name)


def remove_plural_suffix(name):
    parts = name.split()
    if parts and parts[-1].endswith("s") and len(parts[-1]) > 3:
        parts[-1] = parts[-1][:-1]
    return " ".join(parts)
