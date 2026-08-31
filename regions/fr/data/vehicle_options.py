"""Vehicle alternatives for the French Opérateur 112 deployment.

The abbreviations and descriptions mirror the official French vehicle
overview.  Aliases are kept together so the parser can handle either the
short inventory label or the localized description shown on a mission.
"""

from core.vehicle_mapping import get_vehicle_options_from_map


VEHICLE_OPTIONS = {
    "firetruck": ["FPT", "FPTL", "FPTSR", "CCRL", "CCRM", "CCRSR", "CCFS", "CCFM", "CCFL", "VPI"],
    "firetrucks": ["FPT", "FPTL", "FPTSR", "CCRL", "CCRM", "CCRSR", "CCFS", "CCFM", "CCFL", "VPI"],
    "platform truck": ["EPA", "BEA", "Échelle pivotante automatique", "Bras Élevateur Aérien"],
    "battalion chief unit": ["VLCG", "VLCM", "Véhicule léger chef de groupe", "Véhicule Chef de Manoeuvre"],
    "heavy rescue vehicles": ["VSR", "FPTSR", "Véhicule de secours routier", "Véhicule Toute Utilité"],
    "hazmat vehicles": ["VIRT", "VIM", "Véhicule d'Intervention Risques Technologiques", "Véhicule d'Intervention Mousse"],
    "mobile command vehicles": ["VPC", "VCT", "Véhicule Poste de Commandement", "Véhicule de Commandement Transmissions"],
    "mobile air vehicles": ["HELISMUR", "CHOUCAS", "DRAGON", "PELICAN", "DASH MILAN", "HBE"],
    "ambulance": ["VSAV", "ASSU", "VLM", "AR", "AMBU TYPE A", "Véhicule de Secours et d'Assistance aux Victimes"],
    "ems chief": ["VL SSSM", "VLM", "Véhicule de Liaison Médicalisé"],
    "ems mobile command unit": ["PCDSM", "Poste de Commandement Directeur des Secours Médicaux"],
    "ems mobile command units": ["PCDSM", "Poste de Commandement Directeur des Secours Médicaux"],
    "patrol car": ["Véhicule de patrouille", "Véhicule de Patrouille"],
    "police car": ["Véhicule de patrouille", "Véhicule de Patrouille"],
    "police supervisor": ["VR", "Véhicule de Reconnaissance"],
    "police helicopter": ["CHOUCAS", "Hélicoptère"],
    "k-9 unit": ["Équipe cynophile", "VEC"],
    "swat armoured vehicles": ["Fortress 200", "SHERPA LIGHT APC"],
    "wrecker": ["VTU", "Véhicule Toute Utilité"],
    "flatbed carrier": ["VPCE", "Véhicule porte cellule"],
    "water tanker": ["CCRL", "CCRM", "CCGC", "Camion Citerne Grande Capacité"],
    "light boat": ["BLS", "Bateau Léger de Sauvetage"],
    "large rescue boat": ["CTT", "VCSM", "Canot Tous Temps", "Vedette Côtière de Surveillance Maritime"],
    "prisoner transport van": ["VTP (CRS)", "Véhicule de Transports de Prisonniers"],
    "police bus": ["VTP (CRS)", "Véhicule de Transports de Prisonniers"]
}


def get_vehicle_options(vehicle_type):
    return get_vehicle_options_from_map(VEHICLE_OPTIONS, vehicle_type)
