import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://ec2-18-220-40-225.us-east-2.compute.amazonaws.com:8000"

@pytest.fixture(scope="class")
def driver(request):
    # Initialize WebDriver and maximize window
    drv = webdriver.Firefox()
    drv.maximize_window()
    request.cls.driver = drv
    yield
    drv.quit()

@pytest.mark.usefixtures("driver")
class TestTestlinkACC:
    def login(self, username, password):
        # Navigate to login page and authenticate
        self.driver.get(f"{BASE_URL}/login/")
        WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.ID, "username"))
        ).send_keys(username)
        self.driver.find_element(By.ID, "password").send_keys(password)
        self.driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
        WebDriverWait(self.driver, 10).until(
            EC.url_contains("/account/")
        )

    def test_testlinkACC(self):
        # Login with valid credentials
        self.login("testaccount", "testpassword")

        # Resize window for mobile view
        self.driver.set_window_size(550, 700)

        # Start bank-link flow: scroll and click link-button
        link_btn = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.ID, "link-button"))
        )
        self.driver.execute_script("arguments[0].scrollIntoView(true);", link_btn)
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "link-button"))
        )
        self.driver.execute_script("arguments[0].click();", link_btn)

        # Switch into Plaid iframe
        WebDriverWait(self.driver, 10).until(
            EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, "iframe"))
        )

        # Click initial connect button via JS
        connect_btn = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "aut-button"))
        )
        self.driver.execute_script("arguments[0].scrollIntoView(true);", connect_btn)
        self.driver.execute_script("arguments[0].click();", connect_btn)

        # Enter phone number and proceed
        phone_input = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.ID, "rux-enrollment-phone-number-input-input"))
        )
        phone_input.send_keys("(415) 555-0123")
        phone_input.send_keys(Keys.ENTER)

        # Enter OTP code
        otp_input = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.ID, "otp-code-input-input"))
        )
        otp_input.send_keys("123456")
        otp_input.send_keys(Keys.ENTER)

        # Search for institution
        search_input = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.ID, "search-input-input"))
        )
        search_input.send_keys("Pinnacle")
        inst_btn = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#aut-ins_114312 .SearchAndSelectPane-module__buttonFlex"))
        )
        self.driver.execute_script("arguments[0].scrollIntoView(true);", inst_btn)
        self.driver.execute_script("arguments[0].click();", inst_btn)

        # Enter institution credentials and submit via JS
        cred1 = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.ID, "aut-input-0-input"))
        )
        cred1.send_keys("user_good")
        cred2 = self.driver.find_element(By.ID, "aut-input-1-input")
        cred2.send_keys("pass_good")
        cred2.send_keys(Keys.ENTER)

        # Complete flow with JS click
        final_btn = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "aut-button"))
        )
        self.driver.execute_script("arguments[0].scrollIntoView(true);", final_btn)
        self.driver.execute_script("arguments[0].click();", final_btn)

        # Return to main document
        self.driver.switch_to.default_content()

        # Verify success alert and accept
        alert = WebDriverWait(self.driver, 10).until(EC.alert_is_present())
        assert "Successfully linked account" in alert.text
        alert.accept()

        # Navigate calendar controls using JS click to bypass interactability
        prev_btn = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.ID, "prevMonth"))
        )
        self.driver.execute_script("arguments[0].scrollIntoView(true);", prev_btn)
        self.driver.execute_script("arguments[0].click();", prev_btn)

        next_btn = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.ID, "nextMonth"))
        )
        self.driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
        self.driver.execute_script("arguments[0].click();", next_btn)

        # Optional scroll to bottom
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")

  
