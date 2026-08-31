"""Vehicle alternatives used by the Swedish MissionChief deployment."""


VEHICLE_OPTIONS = {
    "firetruck": ["BAS 1", "BAS 2", "släckbil", "Räddningsbil"],
    "firetrucks": ["BAS 1", "BAS 2", "släckbil", "Räddningsbil"],
    "platform truck": ["Stegbil", "Stegbilar"],
    "heavy rescue vehicles": ["Räddningsbil", "Haveribil"],
    "hazmat vehicles": ["Kemskyddsenhet", "Kemskyddsenheter"],
    "mobile command vehicles": ["Räddningsledningsfordon", "Brandbefäl"],
    "mobile air vehicles": ["Luftfordon", "Ambulanshelikopter", "Brandhelikopter"],
    "ambulance": ["Ambulans", "Lättvårdsambulans", "Ambulans Kritisk Transport"],
    "ems chief": ["Akutläkarbil", "Jourläkare", "IVPA"],
    "patrol car": ["Radiobil", "Trafikpolis", "Polismotorcykel", "Cykelpolis"],
    "police car": ["Radiobil", "Trafikpolis", "Polismotorcykel", "Cykelpolis"],
    "police helicopter": ["Polishelikopter"],
    "wrecker": ["Haveribil", "Lastväxlare"],
    "flatbed carrier": ["Haveribil", "Lastväxlare"],
    "water tanker": ["Tankbil"],
    "light boat": ["Liten räddningsbåt"],
    "prisoner transport van": ["Polistransport", "Häktesbuss"],
}


def get_vehicle_options(vehicle_type):
    return VEHICLE_OPTIONS.get(str(vehicle_type).strip().casefold(), [])
