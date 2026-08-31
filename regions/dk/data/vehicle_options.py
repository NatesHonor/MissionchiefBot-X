"""Vehicle alternatives for the Danish Alarmcentral-spil deployment."""

from core.vehicle_mapping import get_vehicle_options_from_map


VEHICLE_OPTIONS = {
    "firetruck": ["Brandbil", "Brandbiler", "Sprøjte", "Autosprøjte", "Tankvogn"],
    "platform truck": ["Stigevogn", "Stigevogne"],
    "battalion chief unit": ["Indsatsleder Brand-køretøj", "Indsatsleder Brand"],
    "heavy rescue vehicles": ["Redningsvogn", "Redningsvogne"],
    "hazmat vehicles": ["Gift- og kemikaliekøretøj", "Gift- og kemikaliekøretøjer", "Kemikaliekøretøj"],
    "mobile command vehicles": ["Ledelses- og kommunikationsmodul", "Ledelses- og kommunikationsmoduler"],
    "ambulance": ["Ambulance", "Ambulancer"],
    "ems chief": ["Akutlægebil", "Akutlægebiler"],
    "patrol car": ["Politibil", "Politibiler"],
    "police supervisor": ["Indsatsleder Politi", "Indsatsleder Politi-køretøj"],
    "police helicopter": ["Politihelikopter", "Politihelikoptere"],
    "k-9 unit": ["Hundepatrulje", "Hundepatruljer"],
    "swat armoured vehicles": ["AKS-køretøj", "AKS køretøjer"],
    "wrecker": ["Vejhjælpskøretøj", "Vejhjælpskøretøjer", "Autohjælpskøretøj"],
    "flatbed carrier": ["Vejhjælpskøretøj", "Autohjælpskøretøj"],
    "water tanker": ["Vandtankvogn", "Vandtankvogne"],
    "light boat": ["Båd", "Både", "Redningsbåd"],
    "prisoner transport van": ["Fangetransportvogn", "Transportvogn", "Politibil"]
}


def get_vehicle_options(vehicle_type):
    return get_vehicle_options_from_map(VEHICLE_OPTIONS, vehicle_type)
