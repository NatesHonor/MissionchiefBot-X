import logging
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

logging.basicConfig(level=logging.INFO)

transport_vehicle_ids = []

def check_transport_needed(driver):
    try:
        transport_alerts = driver.find_elements(By.XPATH, "//div[@class='alert alert-danger' and contains(text(), 'Transport is needed!')]")
        for alert in transport_alerts:
            vehicle_link = alert.find_element(By.XPATH, ".//a[contains(@href, '/vehicles/')]")
            vehicle_id = vehicle_link.get_attribute('href').split('/')[-1]
            logging.info(f"Transport needed for vehicle ID: {vehicle_id}")
            transport_vehicle_ids.append(vehicle_id)
    except NoSuchElementException:
        logging.info("No transport needed alerts found.")
    except Exception as e:
        logging.error(f"Error checking transport needed alerts: {e}")
