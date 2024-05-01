from selenium.webdriver.common.by import By


def process_mission_data(driver, mission_data):
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
    return mission_data
