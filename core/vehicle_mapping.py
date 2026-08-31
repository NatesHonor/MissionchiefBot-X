"""Shared vehicle-name normalization and regional mapping helpers.

MissionChief uses labels such as ``Required Heavy Rescue Vehicles`` on its
mission pages, while the vehicle inventory may contain ``Rescue Engine`` or
``Battalion chief unit``.  The parser also removes a plural suffix from
requirements.  Keeping those rules here prevents every region adapter from
implementing a slightly different lookup algorithm.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping


_PLURAL_TO_SINGULAR = {
    "vehicles": "vehicle",
    "units": "unit",
    "trucks": "truck",
    "engines": "engine",
    "cars": "car",
    "boats": "boat",
    "helicopters": "helicopter",
    "buses": "bus",
}
_SINGULAR_TO_PLURAL = {value: key for key, value in _PLURAL_TO_SINGULAR.items()}
_VEHICLE_UNIT_PAIRS = {
    "vehicle": "unit",
    "unit": "vehicle",
    "vehicles": "units",
    "units": "vehicles",
}


def normalize_vehicle_name(value: object) -> str:
    """Return a punctuation-insensitive, accent-insensitive vehicle key."""

    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(character for character in value if not unicodedata.combining(character))
    value = re.sub(r"[^\w\s]+", " ", value.casefold(), flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def vehicle_name_variants(value: object) -> set[str]:
    """Build safe equivalents for a MissionChief vehicle label.

    This intentionally handles only grammatical variants and the game's
    vehicle/unit wording.  It does not use arbitrary substring matching, which
    could incorrectly combine different vehicle classes such as SWAT SUV and
    SWAT Armoured Vehicle.
    """

    normalized = normalize_vehicle_name(value)
    if not normalized:
        return set()

    variants = {normalized}
    words = normalized.split()
    last = words[-1]
    if last in _PLURAL_TO_SINGULAR:
        variants.add(" ".join((*words[:-1], _PLURAL_TO_SINGULAR[last])))
    elif last in _SINGULAR_TO_PLURAL:
        variants.add(" ".join((*words[:-1], _SINGULAR_TO_PLURAL[last])))

    for index, word in enumerate(words):
        replacement = _VEHICLE_UNIT_PAIRS.get(word)
        if replacement:
            replaced = [*words]
            replaced[index] = replacement
            variants.add(" ".join(replaced))

    # The US/UK game labels both ``firetruck`` and ``fire truck(s)``.
    if "firetruck" in normalized:
        variants.update(
            {
                normalized.replace("firetruck", "fire truck"),
                normalized.replace("firetruck", "fire trucks"),
            }
        )
    if "fire truck" in normalized:
        variants.add(normalized.replace("fire truck", "firetruck"))
    if "policehelicopter" in normalized:
        variants.add(normalized.replace("policehelicopter", "police helicopter"))
    if "police helicopter" in normalized:
        variants.add(normalized.replace("police helicopter", "policehelicopter"))

    # Apply plural/unit substitutions once more to newly-created variants.
    for variant in tuple(variants):
        variant_words = variant.split()
        if not variant_words:
            continue
        variant_last = variant_words[-1]
        if variant_last in _PLURAL_TO_SINGULAR:
            variants.add(
                " ".join((*variant_words[:-1], _PLURAL_TO_SINGULAR[variant_last]))
            )
        elif variant_last in _SINGULAR_TO_PLURAL:
            variants.add(
                " ".join((*variant_words[:-1], _SINGULAR_TO_PLURAL[variant_last]))
            )

    return variants


def dedupe_vehicle_terms(values: Iterable[object]) -> list[str]:
    """Preserve mapping order while removing duplicate normalized terms."""

    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        normalized = normalize_vehicle_name(text)
        if text and normalized and normalized not in seen:
            seen.add(normalized)
            result.append(text)
    return result


def matching_vehicle_alias_group(
    requested: object,
    aliases: Mapping[object, object] | None,
) -> list[str]:
    """Return the complete regional alias group for a requested label."""

    requested_variants = vehicle_name_variants(requested)
    if not requested_variants or not isinstance(aliases, Mapping):
        return []

    for canonical, synonyms in aliases.items():
        if isinstance(synonyms, (str, bytes)) or not isinstance(synonyms, Iterable):
            synonyms = []
        values = dedupe_vehicle_terms((canonical, *synonyms))
        if any(requested_variants & vehicle_name_variants(value) for value in values):
            return values
    return []


def get_vehicle_options_from_map(
    vehicle_options: Mapping[object, object] | None,
    requested: object,
) -> list[str]:
    """Read one regional options table using the shared equivalence rules."""

    if not isinstance(vehicle_options, Mapping):
        return []
    requested_variants = vehicle_name_variants(requested)
    for key, values in vehicle_options.items():
        if not requested_variants & vehicle_name_variants(key):
            continue
        if isinstance(values, (str, bytes)) or not isinstance(values, Iterable):
            return []
        return dedupe_vehicle_terms(values)
    return []


def is_decorated_vehicle_name(requested: Iterable[object], actual: object) -> bool:
    """Match an inventory type with an explicit qualifier in parentheses."""

    actual_text = unicodedata.normalize("NFKD", str(actual or ""))
    actual_text = "".join(
        character for character in actual_text if not unicodedata.combining(character)
    )
    actual_text = re.sub(r"[^\w\s()/-]+", " ", actual_text.casefold())
    actual_text = re.sub(r"\s+", " ", actual_text).strip()
    for value in requested:
        candidate = normalize_vehicle_name(value)
        if candidate and re.match(
            rf"^{re.escape(candidate)}\s*(?:\([^)]*\)|-\s*.+)$",
            actual_text,
        ):
            return True
    return False


def validate_alias_groups(
    aliases: Mapping[object, object] | None,
    label: str = "vehicle",
) -> list[str]:
    """Return human-readable structural errors in an alias map."""

    errors: list[str] = []
    if not isinstance(aliases, Mapping):
        return [f"{label} aliases must be an object"]
    for canonical, synonyms in aliases.items():
        if not str(canonical or "").strip():
            errors.append(f"{label} alias has an empty canonical name")
            continue
        if isinstance(synonyms, (str, bytes)) or not isinstance(synonyms, Iterable):
            errors.append(f"{canonical!r} must contain a list of synonyms")
            continue
        values = [canonical, *synonyms]
        normalized = [normalize_vehicle_name(value) for value in values if str(value or "").strip()]
        if len(normalized) != len(set(normalized)):
            errors.append(f"{canonical!r} contains duplicate aliases")
    return errors


def validate_vehicle_aliases(aliases: Mapping[object, object] | None) -> list[str]:
    """Backward-compatible vehicle alias validator."""

    return validate_alias_groups(aliases, "vehicle")
