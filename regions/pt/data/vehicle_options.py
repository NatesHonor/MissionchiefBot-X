"""Vehicle alternatives used by the Portuguese MissionChief deployment."""


VEHICLE_OPTIONS = {
    "firetruck": ["VFCI", "VLCI", "VUCI", "Veículo de Combate a Incêndios"],
    "firetrucks": ["VFCI", "VLCI", "VUCI", "Veículo de Combate a Incêndios"],
    "platform truck": ["VE", "Veículo Escada", "caminhão plataforma"],
    "heavy rescue vehicles": [
        "VSAT",
        "Veículo de resgate pesado",
        "Veículo de Socorro e Assistência Tático",
    ],
    "hazmat vehicles": [
        "VPME",
        "veículos para produtos perigosos",
        "Veículos de Proteção Multiriscos e Ambiente",
    ],
    "mobile command vehicles": [
        "VCOT",
        "VCOC",
        "Veículo de Comando Tático",
        "Veículo de Comando e Comunicações",
    ],
    "mobile air vehicles": ["Heli INEM", "VCOC"],
    "ambulance": ["ABSC", "Ambulância", "Ambulância de Socorro", "VMER", "SIV"],
    "ems chief": ["VMER", "SIV"],
    "ems mobile command unit": ["VCOC", "Veículo de Comando e Comunicações"],
    "patrol car": ["Carro patrulha", "Carro de Patrulha"],
    "police car": ["Carro patrulha", "Carro de Patrulha"],
    "police helicopter": ["Heli INEM"],
    "wrecker": ["Caminhão de reboque"],
    "flatbed carrier": ["Caminhão de reboque"],
    "water tanker": ["VTTU", "caminhão pipa", "Veículo Tanque"],
    "light boat": ["VIC"],
    "prisoner transport van": ["Carro patrulha"],
}


def get_vehicle_options(vehicle_type):
    return VEHICLE_OPTIONS.get(str(vehicle_type).strip().casefold(), [])
