from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
import random


def transport_submit(driver):
    try:
        driver.get("https://www.missionchief.com")
    except Exception as e:
        print(f"Error navigating to Mission Chief: {e}")
        return

    try:
        transport_requests = driver.find_elements(By.XPATH, "//li[starts-with(@class, 'radio_message_vehicle_')]")
    except Exception as e:
        print(f"Error finding transport requests: {e}")
        return

    vehicle_ids = [request.get_attribute('class').split('_')[-1] for request in transport_requests]
    print(f"Vehicle IDs: {vehicle_ids}")

    for vehicle_id in vehicle_ids:
        try:
            print(f"{vehicle_id}: Transporting")
            vehicle_url = f"https://www.missionchief.com/vehicles/{vehicle_id}"
            driver.get(vehicle_url)
        except Exception as e:
            print(f"Error navigating to vehicle {vehicle_id} page: {e}")
            continue

        try:
            transport_buttons = WebDriverWait(driver, 10).until(
                ec.presence_of_all_elements_located((By.XPATH, "//a[starts-with(@id, 'btn_approach_')]")))
            random.choice(transport_buttons).click()
        except (NoSuchElementException, TimeoutException) as e:
            print(f"btn_approach not found for vehicle {vehicle_id}, checking for btn_success: {e}")
            try:
                success_button = WebDriverWait(driver, 10).until(
                    ec.presence_of_all_elements_located((By.CLASS_NAME, 'btn-success')))
                choice = random.choice(success_button)
                choice.click()
                print(f"Clicked btn_success for vehicle {vehicle_id}.")
            except (NoSuchElementException, TimeoutException) as e:
                print(f"Exception occurred while clicking btn_success for vehicle {vehicle_id}: {e}")
                continue
