from prettytable import PrettyTable
table = PrettyTable()


def display_missions_data(missions_data):
    table.field_names = ["Mission ID", "Title", "Average Credits", "Vehicles", "Patients", "Prisoners", "Crashed Cars"]

    for mission_id, mission_info in missions_data.items():
        vehicles = ", ".join([f"{v}: {c}" for v, c in mission_info['vehicles'].items()])
        table.add_row([mission_id, mission_info['title'], mission_info['average_credits'], vehicles, mission_info['patients'], mission_info['prisoners'], mission_info['crashed_cars']])

    print(table)



def display_final_table(shared_missions_data):
    table = PrettyTable()
    table.field_names = ["Title", "Average Credits", "Vehicles", "Patients", "Prisoners", "Crashed Cars"]

    for m_number, mission_info in shared_missions_data.items():
        title = mission_info['title']
        average_credits = mission_info['average_credits']
        vehicles = mission_info['vehicles']
        patients = mission_info.get('patients', 0)
        prisoners = mission_info.get('prisoners', 0)
        crashed_cars = mission_info.get('crashed_cars', 0)

        vehicle_list = ", ".join([f"{v}: {c}" for v, c in vehicles.items()])
        table.add_row([title, str(average_credits), vehicle_list, str(patients), str(prisoners), str(crashed_cars)])

    print(table)