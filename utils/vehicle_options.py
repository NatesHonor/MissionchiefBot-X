"""US vehicle substitutions.

The regional aliases remain the source of localized names. This table only
contains real cross-category substitutions, and the shared resolver handles
singular/plural and vehicle/unit spelling variants for every region.
"""

from core.vehicle_mapping import get_vehicle_options_from_map


VEHICLE_OPTIONS = {
    "arffs or firetrucks": [
        "Type 1 fire engine",
        "Type 2 fire engine",
        "Small ARFF Crash Tender",
        "Medium ARFF Crash Tender",
        "Large ARFF Crash Tender",
    ],
    "firetruck": ["Type 1 fire engine", "Type 2 fire engine", "Platform truck", "Quint"],
    "firetrucks, heavy rescue vehicles, or platform trucks": [
        "Type 1 fire engine",
        "Type 2 fire engine",
        "Platform truck",
        "Quint",
        "Heavy rescue vehicle",
        "Rescue Engine",
    ],
    "platform truck": ["Platform truck", "Quint"],
    "battalion chief unit": ["Battalion chief unit"],
    "flood equipment": ["Flood Equipment Trailer"],
    "mobile air vehicles": ["Mobile air"],
    "heavy rescue vehicles": ["Heavy rescue vehicle", "Rescue Engine"],
    "hazmat vehicles": ["HazMat"],
    "mobile command vehicles": ["MCV"],
    "fire investigation units": ["Fire Investigator Unit"],
    "arffs": ["Small ARFF Crash Tender", "Medium ARFF Crash Tender", "Large ARFF Crash Tender"],
    "wildland fire engine": [
        "Type 3 engine",
        "Type 4 engine",
        "Type 5 engine",
        "Type 6 engine",
        "Type 7 engine",
    ],
    "wildland fire vehicle": [
        "Type 3 engine",
        "Type 4 engine",
        "Type 5 engine",
        "Type 6 engine",
        "Type 7 engine",
    ],
    "ambulance": ["ALS Ambulance", "BLS Ambulance"],
    "ems chief": ["EMS Chief"],
    "ems mobile command units": ["EMS Mobile Command Unit"],
    "k-9 unit": ["K-9 Unit"],
    "patrol car": ["Patrol car"],
    "riot police unit": ["Riot Police Van", "Riot Police Bus"],
    "police cars or swat suv": ["Patrol car", "SWAT SUV"],
    "sheriff": ["Police Supervisor / Sheriff Unit"],
    "police supervisor / sheriff": ["Police Supervisor / Sheriff Unit"],
    "police helicopter": ["Police helicopter"],
    "atf lab": ["ATF Lab Vehicle"],
    "dea unit": ["DEA Unit"],
    "dea clan lab": ["DEA Clan Lab1"],
    "fbi investigation wagon": ["FBI Investigation Wagon"],
    "fbi unit": ["FBI Unit"],
    "fbi bomb technician vehicle": ["FBI Bomb Technician Vehicle"],
    "fbi drones or fbi investigation wagon": [
        "FBI Investigation Wagon",
        "FBI Surveillance Drone",
    ],
    "swat armoured vehicles": ["SWAT Armoured Vehicle"],
    "light boat": ["Small Coastal Boat", "Large Coastal Boat"],
    "wrecker": ["Wrecker", "Police Wrecker", "Fire Wrecker"],
}


def get_vehicle_options(vehicle_type):
    return get_vehicle_options_from_map(VEHICLE_OPTIONS, vehicle_type)
