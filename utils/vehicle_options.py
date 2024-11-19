def get_vehicle_options(vehicle_type):
    vehicle_options_map = {
        "firetruck": ["Type 1 fire engine", "Type 2 fire engine", "Type 3 fire engine"],
        "platform truck": ["Platform truck", "Quint"],
        "battalion chief vehicle": ["Battalion chief unit"],
        "mobile air unit": ["Mobile air"],
        "mobile air vehicle": ["Mobile air"],
        "heavy rescue vehicle": ["Heavy rescue vehicle", "Rescue Engine"],
        "hazmat vehicle": ["HazMat"],
        "mobile command vehicle": ["MCV"],
        "fire investigation unit": ["Fire Investigator Unit"],
        "ambulance": ["ALS Ambulance", "BLS Ambulance"],
        "police car": ["Patrol car"],
        "police supervisors / sheriff": ["Police Supervisor / Sheriff Unit"],
        "police helicopter": ["Police helicopter"],
        "fbi investigation wagon": ["FBI Investigation Wagon"],
        "riot police unit": ["Riot Police Van", "Riot Police Bus"],
        "warden truck": ["arden's Truck"],
        "police cars or swat suv": ["Patrol car", "SWAT SUV"]
    }
    vehicle_type = vehicle_type.lower()
    return vehicle_options_map.get(vehicle_type, [])
