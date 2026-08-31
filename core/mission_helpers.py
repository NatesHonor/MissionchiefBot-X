"""Pure helpers used while reading mission pages."""


async def get_val(page, selector, split_first=False):
    element = await page.query_selector(selector)
    if not element:
        return 0
    text = (await element.inner_text()).strip().lower()
    try:
        return int(text.split()[0]) if split_first else int(text)
    except (TypeError, ValueError, IndexError):
        return 0


def normalize_name(raw):
    name = raw.lower().replace("required", "").replace("vehicles", "")
    name = name.replace("vehicle", "").strip()
    return remove_plural_suffix(name)


def remove_plural_suffix(name):
    parts = name.split()
    if parts and parts[-1].endswith("s") and len(parts[-1]) > 3:
        parts[-1] = parts[-1][:-1]
    return " ".join(parts)
