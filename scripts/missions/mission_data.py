from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from scripts.missions.fetchdata import process_mission_data
from scripts.missions.utils import handle_alerts, process_missing_personnel, process_missing_vehicles, process_alerts

def gather_mission_data(driver, mission_numbers):
    missions_data = {}
    total_missions = len(mission_numbers)

    for index, mission_number in enumerate(mission_numbers, start=1):
        try:
            mission_url = f"https://www.missionchief.com/missions/{mission_number}"
            print(f"Opening mission {index}/{total_missions}")
            driver.get(mission_url)
            handle_alerts(driver)
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

                mission_data = process_missing_personnel(driver, mission_data)
                mission_data = process_missing_vehicles(driver, mission_data)
                mission_data = process_alerts(driver, mission_data)

                missions_data[mission_number] = mission_data
                if not any([mission_data["personnel"], mission_data["vehicles"]]):
                    missions_data[mission_number] = process_mission_data(driver, mission_data)
        except NoSuchElementException:
            print(f"Mission help button not found for mission {mission_number}, skipping this mission.")
            continue
    return missions_data
