import logging
import time

from selenium.common import WebDriverException

def navigate_to_url(driver, url):
    try:
        driver.get(url)
        time.sleep(2)
    except WebDriverException as e:
        logging.error(f"Error navigating to page {url}: {e.msg}")
        return False
    return True