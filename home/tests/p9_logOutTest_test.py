# Generated by Selenium IDE
import pytest
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

class TestLogOutTest():
  def setup_method(self, method):
    self.driver = webdriver.Firefox()
    self.vars = {}
  
  def teardown_method(self, method):
    self.driver.quit()
  
  def test_logOutTest(self):
    # Test name: Log Out Test
    # Step # | name | target | value
    # 1 | open | http://ec2-18-220-40-225.us-east-2.compute.amazonaws.com:8000/account/ | 
    self.driver.get("http://ec2-18-220-40-225.us-east-2.compute.amazonaws.com:8000/account/")
    # 2 | setWindowSize | 1380x870 | 
    self.driver.set_window_size(1380, 870)
        # 3 | click | id=username | 
    time.sleep(2)
    self.driver.find_element(By.ID, "username").click()
    # 4 | type | id=username | over
    self.driver.find_element(By.ID, "username").send_keys("over")
    # 5 | click | css=.row | 
    time.sleep(2)
    self.driver.find_element(By.CSS_SELECTOR, ".row").click()
    # 6 | click | id=password | 
    time.sleep(2)
    self.driver.find_element(By.ID, "password").click()
    # 7 | type | id=password | over12345
    self.driver.find_element(By.ID, "password").send_keys("over1234")
    # 8 | click | css=.btn | 
    time.sleep(2)
    self.driver.find_element(By.CSS_SELECTOR, ".btn").click()
    # 3 | click | linkText=Logout | 
    time.sleep(2)
    self.driver.find_element(By.LINK_TEXT, "Logout").click()
    # 4 | close |  | 
    self.driver.close()
  
