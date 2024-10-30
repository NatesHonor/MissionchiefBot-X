import os
import json
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def create_ignore_list_file():
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_folder = os.path.join(parent_dir, 'data')
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)
    json_path = os.path.join(data_folder, 'mission_ignore_list.json')
    if not os.path.exists(json_path):
        ignore_list = {
            "ignored_missions": [
                "Cat Stuck in Tree",
                "Car Fire"
            ]
        }
        with open(json_path, 'w') as json_file:
            json.dump(ignore_list, json_file, indent=4)
    return json_path

def load_ignored_missions():
    json_path = create_ignore_list_file()
    with open(json_path, 'r') as json_file:
        ignore_list = json.load(json_file)
    return ignore_list.get("ignored_missions", [])


def total_number_of_missions(driver):
    driver.get("https://www.missionchief.com/")
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'missions')))
    except Exception as e:
        print("Error finding missions id")
    try:
        mission_list = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'mission_list')))
    except Exception as e:
        print("Error: Mission list not found")
        return []

    ignored_missions = load_ignored_missions()
    ignored_missions = [mission.strip().lower() for mission in ignored_missions]
    print(f"Ignored Missions: {ignored_missions}")

    div_elements = mission_list.find_elements(By.CSS_SELECTOR, 'div.mission_panel_red')
    print(f"# of Missions found: {len(div_elements)}")

    mission_numbers = []
    for div in div_elements:
        try:
            mission_caption_link = div.find_element(By.CSS_SELECTOR, 'a.map_position_mover')
            mission_caption = mission_caption_link.text.strip().lower()
            mission_title = mission_caption.split(',')[0].strip()
            if mission_title in ignored_missions:
                print(f"Ignoring Mission: {mission_title}")
                continue

            if "[alliance]" in mission_title:
                print(f"Ignoring Alliance Mission: {mission_title}")
                continue

            dispatch_button = div.find_element(By.CSS_SELECTOR, 'a.mission-alarm-button')
            href = dispatch_button.get_attribute("href")
            mission_number = href.split("/")[-1].split("?")[0]

            if mission_number:
                mission_numbers.append(mission_number)
                print(f"Found Mission Number: {mission_number} - Title: {mission_title}")
            else:
                print(f"Mission Number not found for Title: {mission_title}")
        except Exception as e:
            print(f"Error processing div: {e}")

    return mission_numbers
