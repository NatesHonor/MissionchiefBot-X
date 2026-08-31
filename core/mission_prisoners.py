import re


async def handle_prisoner_transport(page):
    try:
        while True:
            buttons = []
            for division in await page.query_selector_all("div.prison-select"):
                for button in await division.query_selector_all("a.btn-success, a.btn-warning"):
                    buttons.append((await extract_distance(button), button))
            if not buttons:
                return False
            await sorted(buttons, key=lambda item: item[0])[0][1].click()
            await page.wait_for_load_state("networkidle")
    except Exception:
        return False


async def extract_distance(button):
    try:
        match = re.search(
            r"(?:Distance|Entfernung):\s*([\d.,]+)\s*km",
            await button.inner_text(),
            re.IGNORECASE,
        )
        return float(match.group(1).replace(",", ".")) if match else float("inf")
    except (AttributeError, TypeError, ValueError):
        return float("inf")
