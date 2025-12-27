import json, re
from .helpers import normalize_name

with open("data/requirement_mapping.json") as f:
    REQUIREMENT_MAP = json.load(f)

with open("data/personnel_aliases.json") as f:
    PERSONNEL_ALIASES = json.load(f)

def resolve_personnel(name: str) -> str:
    n = name.lower()
    for canonical, synonyms in PERSONNEL_ALIASES.items():
        if n == canonical.lower() or n in [s.lower() for s in synonyms]:
            return canonical
    return name

async def gather_requirements(page):
    reqs = {"vehicles": [], "personnel": [], "liquid": []}

    table = await page.query_selector('div.col-md-4 > table:has(th:has-text("Vehicle and Personnel Requirements"))')
    if table:
        for row in await table.query_selector_all('tr:has(td:has-text("Required"))'):
            n_el = await row.query_selector("td:first-child")
            c_el = await row.query_selector("td:nth-child(2)")
            if n_el and c_el:
                raw = await n_el.text_content()
                name = normalize_name(raw)
                if "probability" in name:
                    continue
                count_text = (await c_el.text_content()).strip().lower()
                try:
                    count = int(count_text)
                except:
                    count = count_text
                category = REQUIREMENT_MAP.get(name, "vehicles")
                if category == "vehicles":
                    reqs["vehicles"].append({"name": name, "count": count})

    table = await page.query_selector('div.col-md-4 > table:has(th:has-text("Other information"))')
    if table:
        for row in await table.query_selector_all("tr"):
            h = await row.query_selector("td:first-child")
            v = await row.query_selector("td:nth-child(2)")
            if h and v:
                header = (await h.inner_text()).lower()
                if "required personnel" in header:
                    html = await v.inner_html()
                    text = re.sub(r'<br\s*/?>', '\n', html)
                    text = re.sub(r'<[^>]+>', '', text)
                    for entry in re.split(r'[,\n]+', text.replace("\xa0", " ")):
                        m = re.match(r'(\d+)\s*x?\s*(.+)', entry.strip())
                        if m:
                            c, n = int(m.group(1)), normalize_name(m.group(2))
                            canonical = resolve_personnel(n)
                            reqs["personnel"].append({"name": canonical, "count": c})
    for p in reqs["personnel"]:
        if p["name"].lower() == "swat personnel":
            div = p["count"] // 6
            if div > 0:
                for v in reqs["vehicles"]:
                    if "swat armoured vehicle" in v["name"].lower():
                        v["count"] = max(0, v["count"] - div)
                reqs["vehicles"] = [v for v in reqs["vehicles"] if not (v["name"].lower().startswith("swat armoured vehicle") and v["count"] == 0)]

    return reqs
