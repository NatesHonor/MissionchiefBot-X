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
            print(f"Ambulance dispatch button not found {vehicle_id}, Trying police dispatch button.")
            try:
                success_button = WebDriverWait(driver, 10).until(
                    ec.presence_of_all_elements_located((By.CLASS_NAME, 'btn-success')))
                choice = random.choice(success_button)
                choice.click()
                print(f"Running Police Transport for {vehicle_id}.")
            except (NoSuchElementException, TimeoutException) as e:
                print(f"Exception occurred while running police transport for {vehicle_id}: {e}")
                try:
                    leave_without_transport_button = WebDriverWait(driver, 10).until(
                        ec.element_to_be_clickable((By.ID, 'leave_without_transport_no_compensation')))
                    leave_without_transport_button.click()
                    print(f"Detected 0 available transport locations, leaving civilian at scene...")
                except (NoSuchElementException, TimeoutException) as e:
                    print(f"Exception occurred while leaving patient at scene {vehicle_id}: {e}")
                    continue
