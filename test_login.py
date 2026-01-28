from browser.driver import Driver
from time import sleep

from network.api.servers.accounts import Account
from tasks.login import Login

identifier = 136
accounts = Account()
data = accounts.show(id=identifier)
profile = data["profile"]

driver = Driver(profile, startUrl=False)
driver.get('https://www.facebook.com/')
driver.new_tab("https://2fa.live")
driver.quit()
driver.switch_to_main()
driver.get('https://www.youtube.com/')
sleep(1000)
# login = Login(driver, data)
# if not login.handle_login():
#     print("Đăng nhập không thành công")
# else:
#     print("Dang nhap thanh cong")

