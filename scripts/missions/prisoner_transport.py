from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

def handle_prisoner_transport(driver):
    try:
        alert_element = driver.find_element(By.ID, "missing_text")
        if "Prisoners must be transported" in alert_element.text:
            print("Prisoners must be transported alert found, handling transport...")
            vehicle_elements = driver.find_elements(By.CLASS_NAME, "vehicle_prisoner_select")
            for vehicle_element in vehicle_elements:
                retry_count = 0
                while retry_count < 3:
                    try:
                        vehicle_id = vehicle_element.get_attribute("vehicle_id")
                        success_buttons = vehicle_element.find_elements(By.CLASS_NAME, "btn-success")
                        if success_buttons:
                            driver.execute_script("arguments[0].scrollIntoView(true);", success_buttons[0])
                            WebDriverWait(driver, 10).until(ec.element_to_be_clickable((By.CLASS_NAME, "btn-success")))
                            success_buttons[0].click()
                            print(f"Clicked success button for vehicle {vehicle_id}")
                            break
                        else:
                            print(f"No success button found for vehicle {vehicle_id}")
                            break
                    except (ElementClickInterceptedException, StaleElementReferenceException):
                        print(f"Retrying click for vehicle due to interception or staleness...")
                        retry_count += 1
                        vehicle_elements = driver.find_elements(By.CLASS_NAME, "vehicle_prisoner_select")
                        if vehicle_elements:
                            vehicle_element = vehicle_elements[0]
                        else:
                            print("No vehicle elements found after retrying.")
                            break
    except NoSuchElementException:
        print("No 'Prisoners must be transported' alert found.")
