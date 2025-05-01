import pytest
import uuid
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class TestCreateAccount:
    @pytest.fixture(autouse=True)
    def setup(self):
        # start browser and maximize for visibility
        self.driver = webdriver.Firefox()
        self.driver.maximize_window()
        yield
        self.driver.quit()

    def test_create_account(self):
        base_url = "http://ec2-18-220-40-225.us-east-2.compute.amazonaws.com:8000/"
        self.driver.get(base_url)

        # 1. Click “Register here” link as soon as it’s clickable
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Register here"))
        ).click()

        # 2. Generate a unique username/email to avoid collisions
        unique = uuid.uuid4().hex[:8]
        username = f"testuser_{unique}"
        email = f"{username}@example.com"
        password = "TestPassword123!"

        # 3. Fill out the form with waits for visibility
        WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.ID, "username"))
        ).send_keys(username)

        self.driver.find_element(By.ID, "email").send_keys(email)
        self.driver.find_element(By.ID, "password1").send_keys(password)
        self.driver.find_element(By.ID, "password2").send_keys(password)

        # 4. Wait for the submit button, scroll into view, then click
        submit_btn = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".btn"))
        )
        # ensure it's in the viewport
        self.driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
        submit_btn.click()

        # 5. Verify that we’re redirected to the account page
        WebDriverWait(self.driver, 10).until(EC.url_contains("/account/"))
        assert "/account/" in self.driver.current_url, "Did not land on account page after sign-up"
