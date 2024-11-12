def get_vehicle_options(vehicle_type):
    vehicle_options_map = {
        "firetruck": ["Type 1 fire engine", "Type 2 fire engine", "Type 3 fire engine"],
        "platform truck": ["Platform truck", "Quint"],
        "battalion chief vehicle": ["Battalion chief unit"],
        "mobile air unit": ["Mobile air"],
        "hazmat vehicle": ["HazMat"],
        "mobile command vehicle": ["MCV"],
        "fire investigation unit": ["Fire Investigator Unit"],
        "ambulance": ["ALS Ambulance", "BLS Ambulance"],
        "policecar": ["Patrol car", "K9 Unit", "SWAT vehicle"],
    }
    vehicle_type = vehicle_type.lower()
    return vehicle_options_map.get(vehicle_type, [])
