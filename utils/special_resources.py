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
    panels = await page.query_selector_all(".mission_panel_red")
    for panel in panels:
        controls = await panel.query_selector_all("a, button, [role='button']")
        for control in controls:
            try:
                metadata = await _control_metadata(control)
                if not is_special_resource_control(metadata):
                    continue
                await control.click(timeout=1500)
                collected += 1
                await asyncio.sleep(0.25)
                if page.url.rstrip("/") != base_url.rstrip("/"):
                    await page.goto(base_url)
                    await page.wait_for_load_state("networkidle")
            except Exception as error:
                display_warning(f"Special resource control could not be collected: {error}")
    return collected
