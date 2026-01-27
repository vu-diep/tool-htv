from browser.driver import Driver
from tasks.login import Login
from network.api.servers.accounts import Account
from vision.xpath import xpaths
from time import sleep

driver = Driver()
driver.get("https://facebook.com", e_wait=5)
print(driver.screenshot())