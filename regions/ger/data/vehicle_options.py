"""Vehicle alternatives used by the German MissionChief deployment."""


VEHICLE_OPTIONS = {
    "firetruck": ["Löschfahrzeug", "Hilfeleistungslöschfahrzeug", "HLF"],
    "firetrucks": ["Löschfahrzeug", "Hilfeleistungslöschfahrzeug", "HLF"],
    "löschfahrzeug": ["Löschfahrzeug", "Hilfeleistungslöschfahrzeug", "HLF"],
    "platform truck": ["Drehleiter", "DLK"],
    "drehleiter": ["Drehleiter", "DLK"],
    "heavy rescue vehicles": ["Rüstwagen", "RW"],
    "rüstwagen": ["Rüstwagen", "RW"],
    "hazmat vehicles": ["Gerätewagen Gefahrgut", "GW-G", "GW-Gefahrgut"],
    "mobile command vehicles": ["Einsatzleitwagen", "ELW 1", "ELW 2"],
    "mobile air vehicles": ["Hubrettungsfahrzeug", "Drehleiter"],
    "ambulance": ["Rettungswagen", "RTW", "Krankentransportwagen", "KTW"],
    "ems chief": ["Notarzteinsatzfahrzeug", "NEF"],
    "ems mobile command unit": ["Einsatzleitwagen", "ELW 1", "ELW 2"],
    "ems mobile command units": ["Einsatzleitwagen", "ELW 1", "ELW 2"],
    "patrol car": ["Streifenwagen"],
    "police car": ["Streifenwagen"],
    "police helicopter": ["Polizeihubschrauber"],
    "wrecker": ["Abschleppwagen", "Abschleppfahrzeug"],
    "flatbed carrier": ["Abschleppwagen", "Abschleppfahrzeug"],
    "water tanker": ["Tanklöschfahrzeug", "TLF", "Löschfahrzeug"],
    "prisoner transport van": ["Gefangenentransportwagen", "Streifenwagen"],
}


def get_vehicle_options(vehicle_type):
    return VEHICLE_OPTIONS.get(str(vehicle_type).strip().casefold(), [])
