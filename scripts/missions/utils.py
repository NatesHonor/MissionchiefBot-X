from selenium.common.exceptions import NoSuchElementException, UnexpectedAlertPresentException, NoAlertPresentException
from selenium.webdriver.common.by import By

def handle_alerts(driver):
    try:
        alert = driver.switch_to.alert
        alert.dismiss()
        print("Unexpected alert dismissed.")
    except NoAlertPresentException:
        pass

def process_missing_personnel(driver, mission_data):
    missing_personnel = driver.find_elements(By.XPATH, '//div[@data-requirement-type="personnel"]')
    if missing_personnel:
        for personnel_element in missing_personnel:
            requirement = personnel_element.text.strip().replace("Missing Personnel: ", "")
            personnels = requirement.split(", ")
            for personnel in personnels:
                number, personnel_type = personnel.split(" ", 1)
                number = number.split("x")[0]
                number_of_personnel = int(number)
                mission_data["personnel"][personnel_type] = number_of_personnel
    return mission_data

def process_missing_vehicles(driver, mission_data):
    missing_vehicles = driver.find_elements(By.XPATH, '//div[@data-requirement-type="vehicles"]')
    if missing_vehicles:
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
    return mission_data

def process_alerts(driver, mission_data):
    ambulancealert = driver.find_elements(By.XPATH,
                                          '//div[@class="alert alert-danger" and contains(text(), "We need: Ambulance")]')
    emschiefalert = driver.find_elements(By.XPATH,
                                         '//div[@class="alert alert-danger" and contains(text(), "We need: EMS Chief")]')
    if ambulancealert:
        for _ in ambulancealert:
            mission_data["vehicles"]["Ambulance"] = mission_data["vehicles"].get("Ambulance", 0) + 1
    if emschiefalert:
        mission_data["vehicles"]["EMS Chief"] = mission_data["vehicles"].get("EMS Chief", 0) + 1
    return mission_data
