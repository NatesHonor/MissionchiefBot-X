"""Vehicle alternatives for the Dutch Meldkamerspel deployment."""

from core.vehicle_mapping import get_vehicle_options_from_map

VEHICLE_OPTIONS = {
    "firetruck": ["Tankautospuit", "TS", "Hulpverleningsvoertuig", "HV"],
    "firetrucks": ["Tankautospuit", "TS", "Hulpverleningsvoertuig", "HV"],
    "platform truck": ["Hoogwerker", "HW"],
    "heavy rescue vehicles": ["Hulpverleningsvoertuig", "HV"],
    "hazmat vehicles": ["Schuimblusvoertuig", "Gevaarlijke stoffen voertuig", "AGS"],
    "mobile command vehicles": ["Commandowagen", "COH"],
    "mobile air vehicles": ["Brandweerhelikopter", "Helikopter"],
    "ambulance": ["Ambulance", "Rapid Responder"],
    "ems chief": ["MOB-arts", "Officier van Dienst Geneeskundig", "OvDG"],
    "ems mobile command unit": ["Commandowagen GHOR", "GNK"],
    "ems mobile command units": ["Commandowagen GHOR", "GNK"],
    "patrol car": ["Politieauto", "Politie voertuig", "Surveillanceauto"],
    "police car": ["Politieauto", "Politie voertuig", "Surveillanceauto"],
    "sheriff": ["Politieauto", "Officier van Dienst Politie", "OvD-P"],
    "police helicopter": ["Politiehelikopter"],
    "riot police unit": ["ME-bus", "ME voertuig"],
    "wrecker": ["Bergingsvoertuig", "Takelwagen", "Weginspectievoertuig"],
    "flatbed carrier": ["Bergingsvoertuig", "Takelwagen"],
    "water tanker": ["Waterwagen", "Tankautospuit", "TS"],
    "light boat": ["Reddingsboot", "Brandweerboot"],
    "prisoner transport van": ["Arrestantenbus", "Politieauto"],
}


def get_vehicle_options(vehicle_type):
    return get_vehicle_options_from_map(VEHICLE_OPTIONS, vehicle_type)
