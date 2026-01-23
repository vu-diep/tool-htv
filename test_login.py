from browser.driver import Driver
from tasks.login import Login
from network.api.servers.accounts import Account
from vision.xpath import xpaths
from time import sleep

# driver = Driver()
# driver.get("https://facebook.com", e_wait=5)
# for xpat_id in xpaths.input_login:
#     input_id = driver.find(
#         query=xpat_id['query'], type_query=xpat_id['type'], send_keys="Login account"
#     )
#     if input_id:
#         break
# # thực hiện tìm kiếm xpath theo password
# for xpat_password in xpaths.input_login_password:
#     input_password = driver.find(
#         query=xpat_password['query'],
#         type_query=xpat_password['type'],
#         send_keys="login_password",
#     )
#     if input_password:
#         break
identifier = 1083
accounts = Account()
account = accounts.show(id=identifier)
profile = account["profile"]
driver = Driver(profile, startUrl=False)
login = Login(driver, account)
if not login.handle_login():
    print("Danh nhap that bai")
else:
    print("Dang nhap thanh cong")
sleep(20)
