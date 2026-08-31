"""Small, dependency-free localization catalog for stable parser terms."""

from __future__ import annotations


_TERMS = {
    "en": {
        "required": ("required", "needed"),
        "personnel": ("required personnel", "personnel needed", "personnel"),
        "average_credits": ("average credits",),
        "max_patients": ("max. patients", "maximum patients"),
        "towed_cars": ("maximum amount of cars to tow", "cars to tow"),
        "prisoner_transport": ("prisoners must be transported", "transport is needed"),
    },
    "de": {
        "required": ("benötigt", "benötigte", "erforderlich", "notwendig"),
        "personnel": ("benötigtes personal", "personal"),
        "average_credits": ("durchschnittliche credits", "durchschnittliche kredite"),
        "max_patients": ("max. patienten", "maximale patienten", "max patienten"),
        "towed_cars": (
            "maximale anzahl abzuschleppender fahrzeuge",
            "fahrzeuge abzuschleppen",
            "abzuschleppende fahrzeuge",
        ),
        "prisoner_transport": (
            "gefangene müssen transportiert werden",
            "gefangene müssen abtransportiert werden",
            "transport wird benötigt",
        ),
    },
    "sv": {
        "required": ("kräver", "behövs", "nödvändigt", "erforderligt"),
        "personnel": ("nödvändig personal", "behövlig personal", "personal"),
        "average_credits": ("genomsnittliga krediter", "genomsnittlig krediter"),
        "max_patients": ("max. patienter", "maximalt antal patienter"),
        "towed_cars": (
            "maximalt antal fordon att bogsera",
            "fordon att bogsera",
            "bogseras",
        ),
        "prisoner_transport": (
            "fångar måste transporteras",
            "fångar ska transporteras",
            "transport krävs",
        ),
    },
}


def get_localized_terms(language: str, category: str) -> tuple[str, ...]:
    """Return localized labels with English fallbacks for mixed-language pages."""

    language_terms = _TERMS.get(str(language or "en").casefold(), {})
    return tuple(
        dict.fromkeys(
            (*language_terms.get(category, ()), *_TERMS["en"].get(category, ()))
        )
    )


def contains_localized_term(value: str, language: str, category: str) -> bool:
    normalized = str(value or "").casefold()
    return any(term in normalized for term in get_localized_terms(language, category))
