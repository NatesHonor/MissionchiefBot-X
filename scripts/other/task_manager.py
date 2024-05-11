from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException


def claim_tasks(driver):
    driver.get("https://www.missionchief.com/tasks/index")

    try:
        claim_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@value='Claim All']"))
        )
        claim_button.click()
        try:
            WebDriverWait(driver, 10).until(
                EC.invisibility_of_element_located((By.XPATH, "//input[@value='Claim All']"))
            )
            print("Claimed all tasks")
        except NoSuchElementException:
            print("Task claiming failed. No tasks available to claim.")

    except NoSuchElementException:
        print("Task claiming failed. No 'Claim All' button found.")

