from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By


def gather_mission_data(driver, mission_numbers):
    missions_data = {}
    total_missions = len(mission_numbers)

    for index, mission_number in enumerate(mission_numbers, start=1):
        try:
            mission_url = f"https://www.missionchief.com/missions/{mission_number}"
            print(f"Opening mission {index}/{total_missions}")
            driver.get(mission_url)
            try:
                driver.find_element(By.ID, f"mission_countdown_{mission_number}")
                print(f"Skipping mission {mission_number} because it's currently in progress!")
                continue
            except NoSuchElementException:
                pass

            images = driver.find_elements(By.TAG_NAME, "img")
            for img in images:
                if "gelb" in img.get_attribute("src"):
                    print(f"Mission {mission_number} currently has units dispatched to it, skipping!")
                    break
            else:
                mission_title = driver.find_element(By.ID, "mission_general_info").get_attribute("data-mission-title")

                mission_data = {"title": mission_title, "average_credits": 100, "vehicles": {}, "personnel": {},
                                "patients": 0, "prisoners": 0, "crashed_cars": 0}

                missing_personnel = driver.find_elements(By.XPATH, '//div[@data-requirement-type="personnel"]')
                missing_vehicles = driver.find_elements(By.XPATH, '//div[@data-requirement-type="vehicles"]')
                patient_elements = driver.find_elements(By.CLASS_NAME, "mission_patient")
                for patient in patient_elements:
                    try:
                        missing_text = patient.find_element(By.XPATH, ".//div[@class='alert alert-danger']").text
                        if "Ambulance" in missing_text:
                            mission_data["vehicles"]["Ambulance"] = mission_data["vehicles"].get("Ambulance", 0) + 1
                        elif "EMS Chief" in missing_text:
                            mission_data["vehicles"]["EMS Chief"] = mission_data["vehicles"].get("EMS Chief", 0) + 1
                    except NoSuchElementException:
                        continue

                if missing_personnel:
                    for personnel_element in missing_personnel:
                        requirement = personnel_element.text.strip().replace("Missing Personnel: ", "")
                        personnels = requirement.split(", ")
                        for personnel in personnels:
                            number, personnel_type = personnel.split(" ", 1)
                            number = number.split("x")[0]
                            number_of_personnel = int(number)
                            mission_data["personnel"][personnel_type] = number_of_personnel
                if missing_vehicles:
                    for vehicle_element in missing_vehicles:
                        requirement = vehicle_element.text.strip().replace("Missing Vehicles: ", "")
                        vehicles = requirement.split(", ")
                        for vehicle in vehicles:
                            number, vehicle_type = vehicle.split(" ", 1)
                            number_of_vehicles = int(number)
                            mission_data["vehicles"][vehicle_type] = number_of_vehicles
                else:
                    mission_help_button = driver.find_element(By.ID, "mission_help")
                    mission_help_button.click()
                    table_rows = driver.find_elements(By.XPATH, '//table[@class="table table-striped"]/tbody/tr')

                    for row in table_rows:
                        columns = row.find_elements(By.TAG_NAME, 'td')
                        requirement = columns[0].text.strip()
                        value = columns[1].text.strip()

                        if ("Required" in requirement and "Station" not in requirement
                                and "Riot Police Extensions" not in requirement
                                and "Fire Marshal's Offices" not in requirement
                                and "SWAT Personnel (In SWAT Vehicles) " not in requirement
                                and "Personnel" not in requirement):
                            if requirement == "Required Personnel Available":
                                personnel_requirements = value.split('\n')
                                for personnel_requirement in personnel_requirements:
                                    number, personnel_type = personnel_requirement.split('x')
                                    personnel_type = personnel_type.replace(number,
                                                                            '').strip()
                                    mission_data["personnel"][personnel_type] = int(number)
                            else:
                                vehicle = requirement.replace("Required ", "")
                                number_of_vehicles = int(''.join([char for char in value if char.isdigit()]))
                                mission_data["vehicles"][vehicle] = number_of_vehicles
                        elif requirement == "Max. Patients":
                            mission_data["patients"] = int(value)
                        elif requirement == "Maximum Number of Prisoners":
                            mission_data["prisoners"] = int(value)
                        elif requirement == "Maximum amount of crashed cars":
                            mission_data["crashed_cars"] = int(value)

                missions_data[mission_number] = mission_data
        except NoSuchElementException:
            print(f"Mission help button not found for mission {mission_number}, skipping this mission.")
            continue

    print(f"Total missions data gathered: {missions_data}")

    return missions_data
