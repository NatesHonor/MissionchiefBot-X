"""Vehicle alternatives used by the German MissionChief deployment.

Leitstellenspiel names vehicles by their short type ("LF 20", "DLK 23",
"ELW 1"), not by the class names used on mission pages ("Löschfahrzeuge",
"Drehleitern"). Each list below names every vehicle type that can fill the
requirement, so the bot can match the player's actual vehicles.
"""

from core.vehicle_mapping import get_vehicle_options_from_map

# Every vehicle that counts as a Löschfahrzeug (fire engine).
_FIRE_ENGINES = [
    "LF 20",
    "LF 10",
    "LF 8/6",
    "LF 20/16",
    "LF 10/6",
    "LF 16-TS",
    "HLF 20",
    "HLF 10",
    "TSF-W",
    "KLF",
    "MLF",
    "Löschfahrzeug",
    "Hilfeleistungslöschfahrzeug",
    "HLF",
]
# The HLF 20 counts as both a Löschfahrzeug and a Rüstwagen.
_HEAVY_RESCUE = ["RW", "HLF 20", "Rüstwagen"]
_PLATFORM_TRUCKS = ["DLK 23", "Drehleiter", "DLK"]
_COMMAND = ["ELW 1", "ELW 2", "Einsatzleitwagen"]
_AMBULANCES = ["RTW", "KTW", "Rettungswagen", "Krankentransportwagen"]
_POLICE_CARS = ["FuStW", "Funkstreifenwagen", "Streifenwagen"]

VEHICLE_OPTIONS = {
    "firetruck": _FIRE_ENGINES,
    "firetrucks": _FIRE_ENGINES,
    "löschfahrzeug": _FIRE_ENGINES,
    "platform truck": _PLATFORM_TRUCKS,
    "drehleiter": _PLATFORM_TRUCKS,
    "heavy rescue vehicles": _HEAVY_RESCUE,
    "rüstwagen": _HEAVY_RESCUE,
    "hazmat vehicles": ["GW-Gefahrgut", "GW-G", "Gerätewagen Gefahrgut"],
    "battalion chief unit": _COMMAND,
    "mobile command vehicles": _COMMAND,
    "mobile air vehicles": ["GW-A", "Gerätewagen Atemschutz"],
    "ambulance": _AMBULANCES,
    "ems chief": ["NEF", "Notarzteinsatzfahrzeug"],
    "ems mobile command unit": _COMMAND,
    "ems mobile command units": _COMMAND,
    "patrol car": _POLICE_CARS,
    "police car": _POLICE_CARS,
    "police helicopter": ["Polizeihubschrauber"],
    "wrecker": ["Abschleppwagen", "Abschleppfahrzeug"],
    "flatbed carrier": ["Abschleppwagen", "Abschleppfahrzeug"],
    "water tanker": ["Tanklöschfahrzeug", "TLF", "Löschfahrzeug"],
    "prisoner transport van": ["GefKw", "Gefangenentransportwagen", "Streifenwagen"],
}


def get_vehicle_options(vehicle_type):
    return get_vehicle_options_from_map(VEHICLE_OPTIONS, vehicle_type)
