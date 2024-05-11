from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from scripts.missions.fetchdata import process_mission_data


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
                ambulancealert = driver.find_elements(By.XPATH,
                                                      '//div[@class="alert alert-danger" and contains(text(), '
                                                      '"We need: Ambulance")]')
                emschiefalert = driver.find_elements(By.XPATH,
                                                     '//div[@class="alert alert-danger" and contains(text(), '
                                                     '"We need: EMS Chief")]')
                skip = False

                if missing_personnel:
                    skip = True
                    for personnel_element in missing_personnel:
                        requirement = personnel_element.text.strip().replace("Missing Personnel: ", "")
                        personnels = requirement.split(", ")
                        for personnel in personnels:
                            number, personnel_type = personnel.split(" ", 1)
                            number = number.split("x")[0]
                            number_of_personnel = int(number)
                            mission_data["personnel"][personnel_type] = number_of_personnel
                if missing_vehicles:
                    skip = True
                    for vehicle_element in missing_vehicles:
                        requirement = vehicle_element.text.strip().replace("Missing Vehicles: ", "")
                        vehicles = requirement.split(", ")
                        for vehicle in vehicles:
                            number, vehicle_type = vehicle.split(" ", 1)
                            number = ''.join(filter(str.isdigit, number))
                            if number:
                                number_of_vehicles = int(number)
                            else:
                                number_of_vehicles = 1
                            mission_data["vehicles"][vehicle_type] = number_of_vehicles

                if ambulancealert:
                    skip = True
                    for _ in ambulancealert:
                        mission_data["vehicles"]["Ambulance"] = mission_data["vehicles"].get("Ambulance", 0) + 1
                if emschiefalert:
                    skip = True
                    mission_data["vehicles"]["EMS Chief"] = mission_data["vehicles"].get("EMS Chief", 0) + 1

                missions_data[mission_number] = mission_data
                if not skip:
                    missions_data[mission_number] = process_mission_data(driver, mission_data)
        except NoSuchElementException:
            print(f"Mission help button not found for mission {mission_number}, skipping this mission.")
            continue

    print(f"Total missions data gathered: {missions_data}")

    return missions_data
