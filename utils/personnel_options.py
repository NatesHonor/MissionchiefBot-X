def get_personnel_options(personnel_type):
    """Vehicles that carry a personnel role, with a fallback crew per vehicle.

    Keys may be exact vehicle types or vehicle classes ("firetruck") that each
    region resolves to its own vehicles. The numbers are only used when the game
    did not report a vehicle's real crew; they are deliberately low so a missing
    crew count sends an extra vehicle instead of too few people.
    """

    personnel_map = {
        "firefighter": {"firetruck": 3},
        "police officer": {"patrol car": 1},
        "traffic control": {
            "Fire Traffic Blocker Unit": 6,
            "Fire Traffic Control Unit": 4,
            "Police Traffic Blocker Unit": 6,
            "Police Traffic Control Unit": 4,
        },
        "hazmat": {"HazMat": 6},
        "swat personnel": {
            "SWAT Armoured Vehicle": 6,
            "SWAT SUV": 4,
        },
        "riot police officer": {
            "Riot Police Bus": 24,
            "Riot Police Van": 12,
        },
        "prisoners": {
            "Police Prisoner Van": 5,
            "Patrol Car": 1,
        },
    }
    personnel_type = str(personnel_type or "").lower()
    return personnel_map.get(personnel_type, {})
