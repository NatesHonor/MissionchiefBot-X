import json
import os
import re
from utils.pretty_print import display_info, display_error

TASKS_FILE = "data/tasks.json"

def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

async def grab_tasks(context, url):
    try:
        page = context.pages[0]
        await page.goto(url + f"/tasks/index")
        await page.wait_for_load_state("networkidle")

        panels = await page.query_selector_all("div.task_panel")
        tasks = []
        seen = set()
        for panel in panels:
            title = ""
            description = ""
            countdown = ""
            progress = ""
            rewards = []

            heading_el = await panel.query_selector(".panel-heading")
            if heading_el:
                title = clean_text(await heading_el.inner_text())

            desc_el = await panel.query_selector(".panel-heading div:nth-child(2)")
            if desc_el:
                description = clean_text(await desc_el.inner_text())

            countdown_el = await panel.query_selector("span[id^='task_countdown']")
            if countdown_el:
                countdown = clean_text(await countdown_el.inner_text())

            progress_el = await panel.query_selector(".progress div[style*='position']")
            if progress_el:
                progress = clean_text(await progress_el.inner_text())

            reward_els = await panel.query_selector_all(".navbar-icon + span")
            for r in reward_els:
                rewards.append(clean_text(await r.inner_text()))

            key = f"{title}|{description}|{progress}"
            if key in seen:
                continue
            seen.add(key)

            tasks.append({
                "title": title,
                "description": description,
                "countdown": countdown,
                "progress": progress,
                "rewards": rewards
            })

        os.makedirs("data", exist_ok=True)
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2, ensure_ascii=False)

        display_info(f"Saved {len(tasks)} unique tasks to {TASKS_FILE}")

        claim_all_form = await page.query_selector("form[action='/tasks/claim_all_rewards']")
        if claim_all_form:
            display_info("Claim All form found, submitting...")
            await claim_all_form.evaluate("(form) => form.submit()")
            await page.wait_for_load_state("networkidle")

        await page.goto(url)
        await page.wait_for_load_state("networkidle")

    except Exception as e:
        display_error(f"Error grabbing tasks: {e}")
