def get_personnel_options(personnel_type):
    personnel_map = {
        "traffic control": {
            "Fire Traffic Blocker Unit": 6,
            "Fire Traffic Control Unit": 4,
            "Police Traffic Blocker Unit": 6,
            "Police Traffic Control Unit": 4,
        },
        "riot police officer": {
            "Riot Police Bus": 24,
            "Riot Police Van": 12,
        },
        "prisoners": {
            "Police Prisoner Van": 5,
            "Patrol Car": 1,
        },
        "sample": {
            "sample1": 1
        },
    }
    personnel_type = personnel_type.lower()
    return personnel_map.get(personnel_type, {})
