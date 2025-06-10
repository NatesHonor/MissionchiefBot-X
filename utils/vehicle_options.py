def get_vehicle_options(vehicle_type):
    vehicle_options_map = {
        "arffs or firetruck": ["Type 1 fire engine", "Type 2 fire engine", "Small ARFF Crash Tender", "Medium ARFF Crash Tender", "Large ARFF Crash Tender"],
        "firetruck": ["Type 1 fire engine", "Type 2 fire engine", "Type 3 fire engine"],
        "firetrucks or playform truck": ["Type 1 fire engine", "Type 2 fire engine","Platform truck", "Quint"],
        "firetrucks, heavy rescue vehicles or platform truck": ["Type 1 fire engine", "Type 2 fire engine", "Platform truck", "Quint", "Heavy rescue vehicle", "Rescue Engine"],
        "platform truck": ["Platform truck", "Quint"],
        "battalion chief vehicle": ["Battalion chief unit"],
        "mobile air": ["Mobile air"],
        "mobile air unit": ["Mobile air"],
        "mobile air vehicle": ["Mobile air"],
        "heavy rescue vehicle": ["Heavy rescue vehicle", "Rescue Engine"],
        "hazmat vehicle": ["HazMat"],
        "mobile command vehicle": ["MCV"],
        "fire investigation unit": ["Fire Investigator Unit"],
        "arff": ["Small ARFF Crash Tender", "Medium ARFF Crash Tender", "Large ARFF Crash Tender"],
        "ambulance": ["ALS Ambulance", "BLS Ambulance"],
        "police car": ["Patrol car"],
        "police supervisors / sheriff": ["Police Supervisor / Sheriff Unit"],
        "police helicopter": ["Police helicopter"],
        "fbi investigation wagon": ["FBI Investigation Wagon"],
        "fbi bomb technician vehicle": ["FBI Bomb Technician Vehicle"],
        "fbi drones or fbi investigation wagon": ["FBI Investigation Wagon", "FBI Surveillance Drone"],
        "riot police unit": ["Riot Police Van", "Riot Police Bus"],
        "warden truck": ["Warden's Truck"],
        "police cars or swat suv": ["Patrol car", "SWAT SUV"],
        "wildland fire engine": ["Type 3 engine", "Type 4 engine", "Type 5 engine", "Type 6 engine", "Type 7 engine"],
        "wildland fire vehicle": ["Type 3 engine", "Type 4 engine", "Type 5 engine", "Type 6 engine", "Type 7 engine"]

    }
    vehicle_type = vehicle_type.lower()
    return vehicle_options_map.get(vehicle_type, [])
