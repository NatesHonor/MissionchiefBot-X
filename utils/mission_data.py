import asyncio, json, os, re
from utils.pretty_print import display_info, display_error

with open('data/requirement_mapping.json') as f:
    REQUIREMENT_MAP = json.load(f)

async def check_and_grab_missions(browsers, num_threads):
    try:
        if os.path.exists('data/mission_data.json'):
            os.remove('data/mission_data.json')
        page = browsers[0].contexts[0].pages[0]
        await page.goto("https://www.missionchief.com")
        panels = await page.query_selector_all('.mission_panel_red')
        if not panels:
            return display_info("No missions found, skipping this function.")
        ids = [(await p.get_attribute('id')).split('_')[-1] for p in panels]
        display_info(f"Found {len(ids)} mission IDs.")
        data = await split_mission_ids_among_threads(ids, browsers, num_threads)
        with open('data/mission_data.json','w') as f:
            json.dump(data, f, indent=4)
        display_info("Mission data collection complete. Stored mission data in mission_data.json.")
    except Exception as e:
        display_error(f"Error gathering mission data: {e}")

async def split_mission_ids_among_threads(ids, browsers, n):
    tasks = [gather_mission_info(ids[i::n], browsers[i], i+1) for i in range(n)]
    results = await asyncio.gather(*tasks)
    return {k:v for r in results for k,v in r.items()}

async def get_val(page, sel, split_first=False):
    el = await page.query_selector(sel)
    if not el: return 0
    text = (await el.inner_text()).strip()
    return int(text.split()[0]) if split_first else int(text)

async def gather_mission_info(ids, browser, tid):
    data, page = {}, browser.contexts[0].pages[0]
    for i, mid in enumerate(ids):
        try:
            display_info(f"Thread {tid}: Grabbing missions {i+1}/{len(ids)}")
            await page.goto(f"https://www.missionchief.com/missions/{mid}")
            await page.wait_for_selector('#missionH1', timeout=5000)
            name_el = await page.query_selector('#missionH1')
            if not name_el: continue
            name = (await name_el.inner_text()).strip()
            miss = await page.query_selector('div.alert-missing-vehicles div[data-requirement-type="vehicles"]')
            if miss:
                parsed, crashed = [], 0
                for entry in (await miss.inner_text()).replace('\xa0',' ').split(','):
                    m = re.search(r'(\d+)\s+(.+)', entry.strip())
                    if m:
                        c,n = int(m.group(1)), normalize_name(m.group(2))
                        if "tow" in n: crashed = c
                        else: parsed.append({"name":n,"count":c})
                data[mid] = {"mission_name":name,"credits":0,"vehicles":parsed,"personnel":[],"liquid":[],"patients":0,"crashed_cars":crashed}
                display_info(f"Thread {tid}: Mission {mid} has missing vehicles.")
                continue
            for alert in await page.query_selector_all('div.alert.alert-danger'):
                txt = (await alert.inner_text()).lower()
                if "prisoners must be transported" in txt or "transport is needed!" in txt:
                    if not await handle_prisoner_transport(page):
                        h4 = await page.query_selector('#h2_prisoners')
                        cnt = int(re.search(r'(\d+)', await h4.inner_text()).group(1)) if h4 else 0
                        data[mid] = {"mission_name":f"Prisoner Transport Mission {mid}","credits":0,"vehicles":[],"personnel":[{"name":"Prisoners","count":cnt}],"liquid":[],"patients":0,"crashed_cars":0}
                        continue
            await page.click('#mission_help')
            await page.wait_for_selector('#iframe-inside-container', timeout=5000)
            requirements = await gather_requirements(page)
            credits = await get_val(page,'td:has-text("Average credits") + td',split_first=True)
            patients = await get_val(page,'td:has-text("Max. Patients") + td')
            crashed = await get_val(page,'td:has-text("Maximum amount of cars to tow") + td')
            if patients: requirements["vehicles"].append({"name":"ambulance","count":patients})
            if patients>=10: requirements["vehicles"].append({"name":"ems chief","count":1})
            if patients>=20: requirements["vehicles"].append({"name":"ems mobile command unit","count":1})
            data[mid] = {"mission_name":name,"credits":credits,"vehicles":requirements["vehicles"],"personnel":requirements["personnel"],"liquid":requirements["liquid"],"patients":patients,"crashed_cars":crashed}
        except Exception as e:
            display_error(f"Error processing mission ID {mid}: {e}")
    return data

def normalize_name(raw: str) -> str:
    name = raw.lower().replace("required","").replace("vehicles","").replace("vehicle","").strip()
    return remove_plural_suffix(name)

def remove_plural_suffix(n):
    parts = n.split()
    last = parts[-1]
    if last.endswith("s") and len(last)>3:
        parts[-1] = last[:-1]
    return " ".join(parts)

async def gather_requirements(page):
    reqs = {"vehicles": [], "personnel": [], "liquid": []}
    table = await page.query_selector('div.col-md-4 > table:has(th:has-text("Vehicle and Personnel Requirements"))')
    if table:
        for row in await table.query_selector_all('tr:has(td:has-text("Required"))'):
            n_el,c_el = await row.query_selector('td:first-child'), await row.query_selector('td:nth-child(2)')
            if n_el and c_el:
                raw = await n_el.text_content()
                name = normalize_name(raw)
                if "probability" in name: continue
                count = int((await c_el.text_content()).strip())
                category = REQUIREMENT_MAP.get(name, "vehicles")
                reqs[category].append({"name":name,"count":count})
    return reqs

async def handle_prisoner_transport(page):
    try:
        while True:
            buttons = [(await extract_distance(btn),btn) for div in await page.query_selector_all('div.prison-select') for btn in (await div.query_selector_all('a.btn-success'))+(await div.query_selector_all('a.btn-warning'))]
            if buttons:
                await sorted(buttons,key=lambda x:x[0])[0][1].click()
                await page.wait_for_load_state('networkidle')
                continue
            return False
    except: return False

async def extract_distance(btn):
    try:
        return float(re.search(r'Distance: ([\d.]+) km', await btn.inner_text()).group(1))
    except: return float('inf')
