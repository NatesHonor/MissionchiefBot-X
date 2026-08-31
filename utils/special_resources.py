"""Collect opt-in event resources shown beside MissionChief missions."""

from __future__ import annotations

import asyncio
import re

from utils.pretty_print import display_warning


RESOURCE_TOKENS = (
    "snowman",
    "valentine",
    "heart",
    "easter",
    "egg",
    "sunflower",
    "pumpkin",
    "santa",
    "christmas",
    "special resource",
)


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def is_special_resource_control(metadata: str) -> bool:
    """Return whether control metadata identifies an event-resource action."""

    normalized = _normalized(metadata)
    if not normalized:
        return False
    if "special resource" in normalized:
        return True
    has_event_action = any(
        marker in normalized
        for marker in ("collect", "claim", "event resource", "event item")
    )
    if has_event_action and "resource" in normalized:
        return True
    return any(token in normalized.split() for token in RESOURCE_TOKENS if " " not in token)


async def _control_metadata(control) -> str:
    return await control.evaluate(
        """
        (element) => {
            const attributes = Array.from(element.attributes || [])
                .filter((attribute) => attribute.name.startsWith('data-'))
                .map((attribute) => `${attribute.name}=${attribute.value}`);
            const images = Array.from(element.querySelectorAll('img'))
                .flatMap((image) => [image.alt, image.src]);
            return [
                element.tagName,
                element.className,
                element.getAttribute('aria-label'),
                element.getAttribute('title'),
                element.getAttribute('href'),
                element.textContent,
                ...attributes,
                ...images,
            ].filter(Boolean).join(' ');
        }
        """
    )


async def collect_special_resources(page, base_url: str) -> int:
    """Click event-resource controls without following ordinary mission links."""

    collected = 0
    # MissionChief has used both ``mission_panel_red`` and ``mission_panel``
    # for the same mission cards.  The older event layout also exposes the
    # pumpkin link directly as ``#easter-egg-link``.
    selector = (
        ".mission_panel_red a, .mission_panel_red button, "
        ".mission_panel_red [role='button'], .mission_panel a, "
        ".mission_panel button, .mission_panel [role='button'], "
        "#mission_list a#easter-egg-link, #missions a#easter-egg-link, "
        "a#easter-egg-link, [data-special-resource], [data-event-resource]"
    )
    attempted = set()
    while True:
        controls = await page.query_selector_all(selector)
        target = None
        for index, control in enumerate(controls):
            try:
                metadata = await _control_metadata(control)
                if not is_special_resource_control(metadata):
                    continue
                identity = await control.evaluate(
                    """(element) => element.id || element.getAttribute('href') ||
                    element.getAttribute('data-resource-id') || element.outerHTML"""
                )
                key = f"{identity}:{index}"
                if key not in attempted:
                    target = (key, control)
                    break
            except Exception as error:
                display_warning(f"Special resource control could not be inspected: {error}")
        if target is None:
            break

        key, control = target
        attempted.add(key)
        try:
            await control.click(timeout=1500)
            collected += 1
            await asyncio.sleep(0.25)
            if page.url.rstrip("/") != base_url.rstrip("/"):
                await page.goto(base_url)
                await page.wait_for_load_state("networkidle")
        except Exception as error:
            display_warning(f"Special resource control could not be collected: {error}")
    return collected
