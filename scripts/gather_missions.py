import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def total_number_of_missions(driver):
    driver.get("https://www.missionchief.com/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'missions')))
    try:
        mission_list = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'mission_list')))
    except Exception as e:
        print("Error: Mission list not found")
        return []

    div_elements = mission_list.find_elements(By.CSS_SELECTOR, 'div.mission_panel_red')
    print(f"# of Missions found: {len(div_elements)}")

    mission_numbers = []
    for div in div_elements:
        try:
            mission_link = div.find_element(By.TAG_NAME, 'a')
            mission_caption = mission_link.text.strip()
            if "[Alliance]" in mission_caption:
                continue

            href = mission_link.get_attribute("href")
            mission_number = href.split("/")[-1].split("?")[0]
            mission_numbers.append(mission_number)
            print(f"Found Mission Number: {mission_number}")
        except Exception as e:
            print(f"Error processing div: {e}")

    return mission_numbers
