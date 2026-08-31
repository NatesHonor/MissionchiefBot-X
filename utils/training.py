"""Config-driven MissionChief school training automation."""

from __future__ import annotations

import re
import unicodedata

from core.settings import TrainingPlan
from utils.pretty_print import display_error, display_info


MAX_EMPLOYEES_PER_ROOM = 10


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]+", " ", value.casefold())).strip()


def _contains(value: str, *terms: str) -> bool:
    normalized = _normalize(value)
    return any(_normalize(term) in normalized for term in terms)


async def _find_school_page(page, base_url: str, school_name: str) -> bool:
    await page.goto(f"{base_url.rstrip('/')}/buildings", wait_until="domcontentloaded")
    links = await page.query_selector_all("a[href*='/buildings/']")
    requested = _normalize(school_name)
    for link in links:
        label = await link.inner_text()
        if requested not in _normalize(label):
            continue
        href = await link.get_attribute("href")
        if not href:
            continue
        await page.goto(
            href if href.startswith("http") else f"{base_url.rstrip('/')}/{href.lstrip('/')}",
            wait_until="domcontentloaded",
        )
        return True
    return False


async def _select_course(page, course_name: str) -> bool:
    requested = _normalize(course_name)
    for select in await page.query_selector_all("select"):
        name = _normalize(
            f"{await select.get_attribute('name') or ''} "
            f"{await select.get_attribute('id') or ''}"
        )
        options = await select.query_selector_all("option")
        for option in options:
            label = await option.inner_text()
            value = await option.get_attribute("value")
            if not value or (requested != "all" and requested not in _normalize(label)):
                continue
            await select.select_option(value=value)
            return True
        if requested == "all" and _contains(name, "training", "schooling", "course"):
            options = await select.query_selector_all("option")
            if options:
                value = await options[0].get_attribute("value")
                if value:
                    await select.select_option(value=value)
                    return True
    return requested == "all"


async def _employee_state(checkbox) -> str:
    return await checkbox.evaluate(
        """element => {
            const row = element.closest('tr, li, .panel, .form-group, .checkbox') || element.parentElement;
            return row ? row.innerText : element.parentElement?.innerText || '';
        }"""
    )


def _priority(state: str, course: str) -> int:
    if _contains(state, "currently training", "in training", "in ausbildung"):
        return 3
    if _contains(state, "not trained", "untrained", "nicht ausgebildet", "keine ausbildung"):
        return 0
    if _contains(state, "already trained", "already educated", "ausgebildet", "abgeschlossen"):
        return 2 if _normalize(course) not in _normalize(state) else 3
    return 1


async def train_school(page, base_url: str, plan: TrainingPlan) -> dict[str, int | str]:
    """Enroll the highest-priority eligible employees for one school course."""

    if not await _find_school_page(page, base_url, plan.school):
        display_error(f"Training school not found: {plan.school}")
        return {"school": plan.school, "course": plan.course, "selected": 0, "skipped": 0}

    forms = await page.query_selector_all("form")
    training_form = None
    for form in forms:
        marker = _normalize(
            f"{await form.get_attribute('action') or ''} {await form.inner_text()}"
        )
        if _contains(marker, "training", "schooling", "course", "ausbildung"):
            training_form = form
            break
    if training_form is None:
        display_error(f"Training form not found at school: {plan.school}")
        return {"school": plan.school, "course": plan.course, "selected": 0, "skipped": 0}

    if not await _select_course(training_form, plan.course):
        display_error(f"Training course not found at {plan.school}: {plan.course}")
        return {"school": plan.school, "course": plan.course, "selected": 0, "skipped": 0}

    candidates = []
    skipped = 0
    for checkbox in await training_form.query_selector_all("input[type='checkbox']"):
        if await checkbox.get_attribute("disabled") is not None:
            skipped += 1
            continue
        state = await _employee_state(checkbox)
        priority = _priority(state, plan.course)
        if priority >= 3:
            skipped += 1
            continue
        candidates.append((priority, checkbox))
    candidates.sort(key=lambda item: item[0])

    capacity = max(1, plan.rooms) * MAX_EMPLOYEES_PER_ROOM
    selected = 0
    for _, checkbox in candidates[:capacity]:
        if await checkbox.is_checked():
            continue
        await checkbox.check()
        selected += 1

    if selected:
        submit = await training_form.query_selector(
            "button[type='submit'], input[type='submit'], button[name*='train'], button[name*='school']"
        )
        if submit:
            await submit.click()
            await page.wait_for_load_state("networkidle")
            display_info(
                f"Scheduled {selected} employees for {plan.course} at {plan.school}."
            )
        else:
            display_error(f"Training submit button not found at {plan.school}")
            selected = 0
    else:
        display_info(f"No eligible employees found for {plan.course} at {plan.school}.")

    return {"school": plan.school, "course": plan.course, "selected": selected, "skipped": skipped}


async def run_training_once(context, base_url: str, plans: tuple[TrainingPlan, ...]) -> list[dict[str, int | str]]:
    if not plans:
        return []
    page = context.pages[0] if context.pages else await context.new_page()
    results = []
    for plan in plans:
        try:
            results.append(await train_school(page, base_url, plan))
        except Exception as error:
            display_error(f"Training error at {plan.school}: {error}")
            results.append({"school": plan.school, "course": plan.course, "selected": 0, "skipped": 0})
    return results
