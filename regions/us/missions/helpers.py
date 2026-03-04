async def get_val(page, sel, split_first=False):
    el = await page.query_selector(sel)
    if not el:
        return 0
    text = (await el.inner_text()).strip().lower()
    try:
        return int(text.split()[0]) if split_first else int(text)
    except:
        return 0

def normalize_name(raw):
    name = raw.lower().replace("required", "").replace("vehicles", "").replace("vehicle", "").strip()
    return remove_plural_suffix(name)

def remove_plural_suffix(n):
    parts = n.split()
    if parts and parts[-1].endswith("s") and len(parts[-1]) > 3:
        parts[-1] = parts[-1][:-1]
    return " ".join(parts)
