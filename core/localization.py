"""Small, dependency-free localization catalog for stable parser terms."""

from __future__ import annotations

import unicodedata


_TERMS = {
    "en": {
        "required": ("required", "needed", "requires"),
        "personnel": ("required personnel", "personnel needed", "personnel"),
        "average_credits": ("average credits",),
        "max_patients": ("max. patients", "maximum patients"),
        "towed_cars": ("maximum amount of cars to tow", "cars to tow"),
        "prisoner_transport": ("prisoners must be transported", "transport is needed"),
        "patient_transport": (
            "transport patient",
            "transport patients",
            "transport to hospital",
            "transport to a hospital",
        ),
        "vehicle_requirements": ("vehicle and personnel requirements",),
        "other_information": ("other information",),
        "selected": ("selected",),
        "distance": ("distance",),
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
        "patient_transport": (
            "patient transportieren",
            "patienten transportieren",
            "patient ins krankenhaus",
            "patienten ins krankenhaus",
        ),
        "vehicle_requirements": ("fahrzeug- und personalanforderungen", "fahrzeuganforderungen"),
        "other_information": ("sonstige informationen", "weitere informationen"),
        "selected": ("ausgewählt", "gewählt"),
        "distance": ("entfernung",),
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
        "patient_transport": (
            "transportera patient",
            "transportera patienter",
            "transportera till sjukhus",
        ),
        "vehicle_requirements": ("fordons- och personalbehov", "fordonskrav"),
        "other_information": ("övrig information", "annan information"),
        "selected": ("vald", "valda"),
        "distance": ("avstånd",),
    },
    "pt": {
        "required": ("necessário", "necessária", "necessários", "requer", "obrigatório"),
        "personnel": ("pessoal necessário", "pessoal necessário", "pessoal"),
        "average_credits": ("créditos médios", "créditos em média"),
        "max_patients": ("máximo de pacientes", "max. pacientes"),
        "towed_cars": (
            "máximo de veículos a rebocar",
            "veículos a rebocar",
            "veículos para rebocar",
        ),
        "prisoner_transport": (
            "os detidos devem ser transportados",
            "detidos devem ser transportados",
            "um transporte é necessário",
        ),
        "patient_transport": (
            "transportar paciente",
            "transportar pacientes",
            "transportar para o hospital",
        ),
        "vehicle_requirements": ("requisitos de veículos e pessoal", "requisitos de veículos"),
        "other_information": ("outras informações", "outra informação"),
        "selected": ("selecionado", "selecionados"),
        "distance": ("distância",),
    },
    "nl": {
        "required": ("vereist", "nodig", "benodigd", "moet"),
        "personnel": ("benodigd personeel", "personeel nodig", "personeel"),
        "average_credits": ("gemiddelde credits",),
        "max_patients": ("max. patiënten", "maximum aantal patiënten"),
        "towed_cars": ("maximaal aantal auto's om te slepen", "auto's om te slepen"),
        "prisoner_transport": (
            "gevangenen moeten worden vervoerd",
            "transport is nodig",
        ),
        "patient_transport": (
            "patiënt vervoeren",
            "patiënten vervoeren",
            "naar het ziekenhuis vervoeren",
        ),
        "vehicle_requirements": ("voertuig- en personeelsvereisten", "voertuigvereisten"),
        "other_information": ("overige informatie", "andere informatie"),
        "selected": ("geselecteerd",),
        "distance": ("afstand",),
    },
    "da": {
        "required": ("kræver", "påkrævet", "nødvendig", "behøves"),
        "personnel": ("påkrævet personale", "nødvendigt personale", "personale"),
        "average_credits": ("gennemsnitlige credits",),
        "max_patients": ("maks. patienter", "maksimalt antal patienter"),
        "towed_cars": ("maksimalt antal biler der skal bugseres",),
        "prisoner_transport": ("fanger skal transporteres", "transport er nødvendig"),
        "patient_transport": (
            "transporter patient",
            "transporter patienter",
            "til hospitalet",
        ),
        "vehicle_requirements": ("krav til køretøjer og personale", "køretøjskrav"),
        "other_information": ("andre oplysninger",),
        "selected": ("valgt",),
        "distance": ("afstand",),
    },
    "fr": {
        "required": ("requis", "nécessaire", "nécessaires"),
        "personnel": ("personnel requis", "personnel nécessaire", "personnel"),
        "average_credits": ("crédits moyens",),
        "max_patients": ("patients max.", "nombre maximal de patients"),
        "towed_cars": ("nombre maximum de voitures à remorquer",),
        "prisoner_transport": ("les prisonniers doivent être transportés",),
        "patient_transport": (
            "transporter le patient",
            "transporter des patients",
            "vers l'hôpital",
        ),
        "vehicle_requirements": ("besoins en véhicules et personnel",),
        "other_information": ("autres informations",),
        "selected": ("sélectionné",),
        "distance": ("distance",),
    },
    "it": {
        "required": ("richiesto", "necessario", "necessari"),
        "personnel": ("personale richiesto", "personale necessario", "personale"),
        "average_credits": ("crediti medi",),
        "max_patients": ("pazienti max.", "numero massimo di pazienti"),
        "towed_cars": ("numero massimo di auto da trainare",),
        "prisoner_transport": ("i prigionieri devono essere trasportati",),
        "patient_transport": (
            "trasporta il paziente",
            "trasportare il paziente",
            "trasportare all'ospedale",
        ),
        "vehicle_requirements": ("requisiti di veicoli e personale",),
        "other_information": ("altre informazioni",),
        "selected": ("selezionato",),
        "distance": ("distanza",),
    },
    "pl": {
        "required": ("wymagane", "potrzebne", "wymaga"),
        "personnel": ("wymagany personel", "potrzebny personel", "personel"),
        "average_credits": ("średnia liczba kredytów",),
        "max_patients": ("maks. liczba pacjentów",),
        "towed_cars": ("maksymalna liczba samochodów do holowania",),
        "prisoner_transport": ("więźniowie muszą być transportowani",),
        "patient_transport": (
            "transportuj pacjenta",
            "transportować pacjenta",
            "transport do szpitala",
        ),
        "vehicle_requirements": ("wymagania dotyczące pojazdów i personelu",),
        "other_information": ("inne informacje",),
        "selected": ("wybrano",),
        "distance": ("odległość",),
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


def _fold(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(character for character in value if not unicodedata.combining(character)).casefold()


def contains_localized_term(value: str, language: str, category: str) -> bool:
    normalized = _fold(value)
    return any(_fold(term) in normalized for term in get_localized_terms(language, category))
