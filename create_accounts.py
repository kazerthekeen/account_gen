import fileinput
import csv
import json
from time import sleep
from selenium import webdriver
from selenium.common.exceptions import (
    StaleElementReferenceException,
    NoAlertPresentException,
    UnexpectedAlertPresentException,
    TimeoutException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.select import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

ARROW_DOWN = u"\ue015"

"""
This can be used to make a bunch of accounts for a vendor, reads in from a csv file
defined 'auto_accout.json'. The Csv file should have 3 columns labeled as:

lastname firstname email

The columns can be in any order but need to be labeled as shown above. This is
case sensative.
The other account details need to be defined in auto_accout.json then file can be run.

Note this has been condensed from several files to be a stand alone script.
"""


class driver_manager:
    def __init__(self, config, delay=30):
        if config["browser_type"] == "Firefox":
            self.set_firefox_driver(config)
        elif config["browser_type"] == "Chrome":
            self.set_chrome_driver(config)
        else:
            self.driver = None
        self.driver.delete_all_cookies()
        self.delay = delay

    def set_chrome_driver(self, config):
        self.driver = webdriver.Chrome(executable_path=config["chrome_executable_path"])

    def set_firefox_driver(self, config):
        binary = FirefoxBinary(config["firefox_browser_bin"])
        self.driver = webdriver.Firefox(firefox_binary=binary, executable_path=config["firefox_executable_path"])

    def submit_value_by_id(self, id, value, clear=True, submit=False):
        elem = self.driver.find_element_by_id(id)
        self.__submit(elem, value, clear, submit)

    def select_value_by_id(self, id, value, tries=0):
        try:
            elem = self.driver.find_element_by_id(id)
            for option in elem.find_elements_by_tag_name("option"):
                if option.text == value:
                    break
                else:
                    elem.send_keys(ARROW_DOWN)
        except StaleElementReferenceException as e:
            if tries > 3:
                raise e
            self.sleep(1)
            self.select_value_by_id(id, value, tries + 1)

    def __submit(self, elem, value, clear, submit):
        if clear:
            elem.clear()
            self.wait()
        elem.send_keys(value)
        self.wait()
        if submit:
            elem.submit()
            self.wait()

    def wait(self, timeout=-1, condition=None):
        if condition is not None:
            return WebDriverWait(self.driver, timeout).until(condition)
        else:
            if timeout < 0:
                timeout = self.delay
            self.driver.implicitly_wait(timeout)

    def click_by(self, by_Ref, timeout=5):
        elem = self.wait(timeout, EC.element_to_be_clickable(by_Ref))
        elem.click()
        self.wait()

    def get(self, value, timeout=5):
        self.driver.get(value)
        sleep(1)

        try:
            alert = self.driver.switch_to.alert
            alert.accept()
        except NoAlertPresentException:
            pass
        finally:
            self.wait(timeout, EC.url_contains(value))

    def value_in_source(self, value):
        return value in self.driver.page_source

    def sleep(self, t):
        sleep(t)

    def quit(self):
        self.driver.quit()

    def scroll_bottom(self):
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")


class mdpocket_web:

    input_keys = {
        "default": {
            "firstname": "input-firstname",
            "lastname": "input-lastname",
            "email": "input-email",
            "telephone": "input-telephone",
            "address-1": "input-address-1",
            "postcode": "input-postcode",
            "address-2": "input-address-2",
            "company": "input-company",
            "country": "input-country",
            "city": "input-city",
            "zone": "input-zone",
        },
        "payment": {
            "firstname": "input-payment-firstname",
            "lastname": "input-payment-lastname",
            "email": "input-payment-email",
            "telephone": "input-payment-telephone",
            "address-1": "input-payment-address-1",
            "postcode": "input-payment-postcode",
            "address-2": "input-payment-address-2",
            "company": "input-payment-company",
            "country": "input-payment-country",
            "city": "input-payment-city",
            "zone": "input-payment-zone",
        },
    }

    def make_account(self, dm, user):
        dm.get("https://mdpocket.com/index.php?route=account/register")
        self.__input_personal_details(dm, user)
        self.__input_address(dm, user)
        dm.submit_value_by_id("input-password", user["password"])
        dm.submit_value_by_id("input-confirm", user["confirm"])
        dm.scroll_bottom()
        dm.click_by((By.ID, "address-validate"))
        try:
            dm.click_by((By.ID, "i-agree"))
        except TimeoutException:
            dm.click_by((By.XPATH, "//div[contains(text(),'Keep Original')]"))
        dm.click_by((By.NAME, "agree"))
        dm.click_by((By.XPATH, "//input[@value='Continue']"))

    def __input_personal_details(self, dm, user, input_type="default"):
        key = self.input_keys[input_type]
        dm.submit_value_by_id(key["firstname"], user["firstname"])
        dm.submit_value_by_id(key["lastname"], user["lastname"])
        dm.submit_value_by_id(key["email"], user["email"])
        dm.submit_value_by_id(key["telephone"], user["telephone"])

    def __input_address(self, dm, user, input_type="default"):
        key = self.input_keys[input_type]
        dm.submit_value_by_id(key["address-1"], user["address-1"])
        dm.submit_value_by_id(key["postcode"], user["postcode"])
        dm.submit_value_by_id(key["city"], user["city"])
        dm.select_value_by_id(key["zone"], user["zone"])


def load_settings(file_name="testing.json"):
    with open(file_name, "r") as file:
        s = file.read()
    settings = json.loads(s)
    return settings


def Make_Accounts():
    config = load_settings("auto_account.json")
    users = parse_users(config["load_file"], config["protoype"])
    site = mdpocket_web()
    for user in users:
        print(user)
        dm = driver_manager(config)
        try:
            site.make_account(dm, user)
            dm.sleep(10)
            assert dm.value_in_source("Your Account Has Been Created!")
            dm.quit()
            print("User success")
        except TimeoutException:
            print("User failed")
            break
        except AssertionError:
            print("User already created")
        finally:
            dm.quit()


def parse_users(file_name, protoype):
    users = []
    with open(file_name, "r") as file:
        reader = csv.DictReader(file)
        for user in reader:
            user.update(protoype)
            users.append(user)
    return users


if __name__ == "__main__":
    Make_Accounts()
