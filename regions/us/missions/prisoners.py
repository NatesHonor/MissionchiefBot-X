import re

async def handle_prisoner_transport(page):
    try:
        while True:
            buttons = []
            for div in await page.query_selector_all("div.prison-select"):
                for btn in await div.query_selector_all("a.btn-success, a.btn-warning"):
                    buttons.append((await extract_distance(btn), btn))
            if buttons:
                await sorted(buttons, key=lambda x: x[0])[0][1].click()
                await page.wait_for_load_state("networkidle")
                continue
            return False
    except:
        return False

async def extract_distance(btn):
    try:
        return float(re.search(r"Distance: ([\d.]+) km", await btn.inner_text()).group(1))
    except:
        return float("inf")
