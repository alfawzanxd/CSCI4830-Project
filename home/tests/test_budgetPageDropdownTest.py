import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
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
class TestBudgetPageDropdownTest:
    def login(self, username, password):
        # Log in and ensure landing on account page
        self.driver.get(f"{BASE_URL}/login/")
        WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.ID, "username"))
        ).send_keys(username)
        self.driver.find_element(By.ID, "password").send_keys(password)
        self.driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
        WebDriverWait(self.driver, 10).until(EC.url_contains("/account/"))

    def test_budget_page_dropdown(self):
        # Use existing user credentials
        self.login("over", "over1234")

        # Navigate to the budget section
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Budget"))
        ).click()

        # Define all expected options to iterate through
        options = [
            "Credit Card (Pinnacle Bank - Personal)",
            "401k (Pinnacle Bank - Personal)",
            "HSA (Pinnacle Bank - Personal)",
            "Business Credit Card (Pinnacle Bank - Personal)"
        ]

        for label in options:
            # Re-locate the dropdown each iteration to avoid stale references
            select_elem = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.NAME, "account"))
            )
            select = Select(select_elem)
            select.select_by_visible_text(label)

            # Verify selected option via CSS pseudo-class
            selected_option = WebDriverWait(self.driver, 10).until(
                lambda d: d.find_element(By.CSS_SELECTOR, "select[name='account'] option:checked")
            )
            assert selected_option.text == label

        # If we reach here, the dropdown works as expected
        assert True

