from time import sleep
from datetime import datetime
import pytz
import traceback

from .check_point import HandleCheckpoint
from network.api.servers.proxies import Proxies
from network.api.servers.accounts import Account
from vision.xpath import xpaths, xpath_login
from utils.root import RootManager


class Login:
    # Constants
    FACEBOOK_URL = "https://www.facebook.com/?locale=en_US"
    BLOCK_MESSAGES = [
        "your account has been locked",
        "We suspended your account",
        "Account locked",
        "You’re Temporarily Blocked",
    ]
    MAX_LOGIN_ATTEMPTS = 3
    RETRY_DELAY = 60
    WAIT_TIMEOUT = 5

    def __init__(self, driver, account):
        self.driver = driver
        self.last_notify_time = None
        self.account = account
        self.account_name = account.get("name")
        self.cookies = account.get("latest_cookie", None)
        if self.cookies is not None:
            self.cookies = self.cookies.get("cookies")
        self.profiles = account["profile"]
        self.check_point = HandleCheckpoint(self.driver)
        self.proxies = Proxies()
        self.accounts = Account()
        self.root_manager = RootManager()
        self.yolo = driver.yolo_reader(model_path=self.root_manager.get_full_url_user('vision/models/login.pt'))

    def check_block(self):
        """Check if the account is blocked or temporarily blocked."""
        try:
            self.driver.page.wait_for_selector("body", timeout=self.WAIT_TIMEOUT)
            self.driver.clickOk()  # Assume this is a custom method
            for message in self.BLOCK_MESSAGES:
                if self.driver.find(f"//*[contains(text(), '{message}')]"):
                    if message == "You’re Temporarily Blocked" and self.check_login():
                        self.driver.get(f"{self.FACEBOOK_URL}/home.php")
                        self.driver.clickOk()
                        if not self.driver.find(f"//*[contains(text(), '{message}')]"):
                            return False
                    return True
            return False
        except:
            return False

    def check_login(self):
        """Check if the user is logged in by finding profile elements."""
        for selector in xpath_login.profile_selectors:
            if self.driver.find(selector):
                return True
        return False

    def login_with_user_pass(self):
        """Attempt login using username and password."""
        try:
            recent_login = self.driver.find(xpath_login.recent_login)
            if recent_login is not None:
                recent_login.click()
                
            login_account = self.account.get("login_account", "")
            login_password = self.account.get("login_password", "")
            
            # Thực hiện login bằng AI
            try:
                # click ra ngoài để loại bỏ forcus giúp AI nhận rõ hơn
                self.driver.click_mouse(10, 10)
                img_bytes = self.driver.screenshot(path="")
                result = self.yolo.detect(img_bytes=img_bytes)
                print('result: ', result)
                mat_khau = result['mat_khau']
                nut_dang_nhap = result['nut_dang_nhap']
                tai_khoan = result['tai_khoan']
                self.driver.click_mouse(tai_khoan['center_x'], tai_khoan['center_y'])
                self.driver.send_keys(login_account)
                self.driver.click_mouse(mat_khau['center_x'], mat_khau['center_y'])
                self.driver.send_keys(login_password)
                self.driver.click_mouse(nut_dang_nhap['center_x'], nut_dang_nhap['center_y'])
            except Exception as e:
                # chụp ảnh lỗi
                self.driver.screenshot("resources/error_img/login_with_user_pass.png")
                print("Loi khi login bang AI chuyen sang xpath", e)
                
                # thực hiện tìm kiếm xpath theo id
                for xpat_id in xpath_login.input_login:
                    input_id = self.driver.find(
                        query=xpat_id["query"],
                        type_query=xpat_id['type'],
                        send_keys=login_account,
                    )
                    if input_id:
                        break
                # thực hiện tìm kiếm xpath theo password
                for xpat_password in xpath_login.input_login_password:
                    input_password = self.driver.find(
                        query=xpat_password["query"],
                        type_query=xpat_password['type'],
                        send_keys=login_password,
                    )
                    if input_password:
                        break
                # thực hiện tìm kiếm xpath theo button login
                for xpat_button_login in xpath_login.button_login:
                    input_password = self.driver.find(
                        query=xpat_button_login["query"],
                        type_query=xpat_button_login['type'],
                    )
                    if input_password:
                        input_password.click()
                        break

            self.handle_post_login()
            # kiểm tra và cập nhật ngôn ngữ
            self.driver.get(self.FACEBOOK_URL)
            self.check_and_set_english_locale()
        except Exception as e:
            print("Loi khi login_with_user_pass: ", e)
        return self.check_login()

    def handle_post_login(self):
        """Handle post-login steps like cookies, captcha, and 2FA."""
        try:
            self.driver.page.wait_for_selector("body", timeout=self.WAIT_TIMEOUT)
        except:
            pass
        self.accept_cookies()
        # nếu phát hiện from chứa capcha thì sẽ dừng một lúc để giải
        try:
            # Tìm iframe chứa recaptcha
            self.driver.page.wait_for_selector('//iframe[@id="captcha-recaptcha', timeout=self.WAIT_TIMEOUT)
            print("phat hien capcha doi 30s de tiep tuc")
            sleep(60)
        except Exception as e:
            pass

        sleep(15)
        self.handle_check2fa()
        sleep(10)
        self.save_profile()

        self.driver.click_text("Trust this device", wait=self.WAIT_TIMEOUT)
        self.driver.click_text("Dismiss", wait=self.WAIT_TIMEOUT)

    def accept_cookies(self):
        """Accept all cookies if prompted."""
        try:
            accept_button = self.driver.find_all(xpath_login.allow_all_cookies, last=True)
            if accept_button:
                accept_button.click()
        except:
            pass

    def handle_check2fa(self):
        try:
            try:
                img_bytes = self.driver.screenshot(path="")
                result = self.yolo.detect(img_bytes=img_bytes)
                print('result: ', result)
                nut_tiep_tuc = result['nut_tiep_tuc']
                ma_xac_thuc_2FA = result['ma_xac_thuc_2FA']
                code = self.get_code_from_2fa(self.account.get("keyword_2fa"))
                print("code: ", code)
                self.driver.click_mouse(ma_xac_thuc_2FA['center_x'], ma_xac_thuc_2FA['center_y'])
                self.driver.send_keys(code)
                self.driver.click_mouse(nut_tiep_tuc['center_x'], nut_tiep_tuc['center_y'])
            except Exception as e:
                print("Loi khi check trong handle_check2fa: ", e)
                
                btn_try_another_way = self.driver.find(xpath_login.btn_try_another_way)
                flat_check_2fa = False
                if btn_try_another_way:
                    btn_try_another_way.click()
                    sleep(3)
                    for xpath_bttn_atuthen in xpath_login.btn_authentication_app:
                        btn = self.driver.find(xpath_bttn_atuthen, type_query = "tag_name")
                        if btn:
                            btn.click()
                            break

                    btn_continue = None
                    for xpath_continue in xpath_login.xpath_continues:
                        btn_continue = self.driver.find(xpath_continue)
                        if btn_continue is not None:
                            break
                    if btn_continue is not None:
                        try:
                            btn_continue.click()
                            self.driver.click_script(btn_continue)
                            flat_check_2fa = True
                        except Exception as e:
                            print("Loi khi click continue trong handle_check2fa: ")
                sleep(3)
                authen_app = None
                for xpath in xpath_login.xpath_authen_app:
                    authen_app = self.driver.find(xpath)
                    if authen_app:
                        break

                if authen_app or flat_check_2fa:
                    code = self.get_code_from_2fa(self.account.get("keyword_2fa"))
                    self.push_code(code)
        except Exception as e:
            print("Loi o handle_check2fa: ", e)
            

    def save_profile(self):
        try:
            self.driver.find(xpath_login.save_your_login_info)
            save = self.driver.find(xpath_login.save)
            save.click()
        except Exception as e:
            print(
                'Khong tim thay xpath: //span[text()="Save your login info? hoac //div[@aria-label="Save"]"]'
            )
            pass

    def get_code_from_2fa(self, two_fa):
        """Retrieve 2FA code from 2fa.live."""
        try:
            self.driver.new_tab("https://2fa.live")
            self.driver.find("listToken", type_query="id", send_keys=two_fa)
            self.driver.find(xpath_login.submit_2falive).click()
            sleep(10)
            code_element = self.driver.find(xpath_login.code_2falive)
            code_value = code_element.get_attribute("value")
            if code_value is None:
                code_value = code_element.input_value()
            code = code_value.split("|")[-1]
            self.driver.switch_to_main()
            return code
        except Exception as e:
            print(f"Error retrieving 2FA code: {e}")
            self.driver.switch_to_main()
            return None

    def push_code(self, code):
        """Input code for captcha or 2FA."""
        if code:
            try:
                input_field = self.driver.find(xpath_login.imput_authentication_app, send_keys=code)
                if input_field:
                    sleep(3)
                    for xpat_continue in xpath_login.btn_continues:
                        element = self.driver.find(xpat_continue, type_query="tag_name")
                        if element is not None:
                            element.click()
            except Exception as e:
                print("Failed to input code: ", e)
                traceback.print_exc()

    def login(self):
        """Main login logic with cookie and user/pass fallback."""
        check_block = self.check_block()
        check_login = self.check_login()
        if check_login:
            return check_block, True

        # if self.cookies:
        #     self.driver.set_cookies(self.cookies)
        #     self.driver.get(self.FACEBOOK_URL)
        #     self.accept_cookies()
        #     check_block, check_login = self.check_block(), self.check_login()
        if not check_login:
            # kiêm tra xem có tồn tại yêu cầu sử dụng profile//span[text()="Use another profile"]
            btn_use_profile = self.driver.find(xpath_login.btn_use_profile)
            if btn_use_profile:
                btn_use_profile.click()
                sleep(5)
            check_login = self.login_with_user_pass()

        return check_block, check_login

    def handle_login(self):
        """Handle login with retry logic (gửi tin nhắn sau khi thử hết lượt)."""

        action = self.driver.action_send_error
        attempts = 0
        tz = pytz.timezone("Asia/Ho_Chi_Minh")
        login_success = False
        message_to_send = None  # 🔥 CHỈ gửi 1 lần
        update_data = {}  # 🔥 CHỈ update account 1 lần

        while attempts < self.MAX_LOGIN_ATTEMPTS:

            if not self.account:
                raise Exception("Không thể lấy thông tin profile hoặc account")

            try:
                # --- Truy cập trang Facebook ---
                try:
                    self.driver.get(self.FACEBOOK_URL)
                    self.click_check_cookie()
                except Exception:
                    proxy_id = self.profiles.get("proxy_id")
                    proxy = self.profiles.get("proxy")
                    self.proxies.update(id=proxy_id, data={"status": 2})

                    message_to_send = (
                        f"Proxy {proxy.get('ip')}:{proxy.get('port')} không thể truy cập Internet. "
                        f"Tài khoản: {self.account.get('name')}. Vui lòng kiểm tra!"
                    )
                    update_data = {"status_login": 1}
                    break  # 🔥 Nhảy ra luôn, không thử lại

                sleep(10)

                # --- Kiểm tra checkpoint ---
                status_check_point, code_check = self.check_point.start()
                if status_check_point:
                    message_to_send = (
                        f"Tài khoản {self.account_name} bị checkpoint loại {code_check}"
                    )
                    update_data = {"status_login": 1, "checkpoint": code_check}
                    break

                self.check_and_set_english_locale()

                # --- Thực hiện login ---
                check_block, check_login = self.login()
                self.click_check_cookie()
                if check_login:
                    login_success = True
                    self.cookies = self.driver.get_cookies()

                    update_data = {
                        "status_login": 0,
                        "notification_status": 0,
                        "checkpoint": 0,
                        "last_login": datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S"),
                        "cookie": self.driver.get_cookies(),
                    }
                    break  # 🔥 Thành công → thoát vòng lặp

                # --- LOGIN FAIL ---
                attempts += 1
                update_data = {
                    "status_login": 1,
                    "notification_status": 1,
                    "last_login": datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S"),
                    "checkpoint": 0,
                }

                sleep(self.RETRY_DELAY)

            except Exception:
                attempts += 1
                update_data = {"status_login": 6}

            except Exception as e:
                status_check_point, code_check = self.check_point.start()
                if status_check_point:
                    message_to_send = (
                        f"Tài khoản {self.account_name} bị checkpoint loại {code_check}"
                    )
                    update_data = {"status_login": 1, "checkpoint": code_check}
                    break

                raise Exception(f"Không thể đăng nhập tài khoản: {e}")

        # ========== SAU KHI KẾT THÚC (DÙ THÀNH CÔNG HAY THẤT BẠI) ==========

        # 🔥 Update account 1 lần duy nhất
        if update_data:
            self.accounts.update(self.account.get("id"), update_data)

        # 🔥 Chỉ gửi 1 lần Telegram
        if not login_success and message_to_send:
            current_time = datetime.now().timestamp()
            if not self.last_notify_time or current_time - self.last_notify_time >= 900:
                self.driver.send_image_error(
                    f"{self.account.get('name', '')} Lỗi đăng nhập khi đăng bài!"
                )
                self.driver.send_message_telegram(
                    message_to_send, group="check", action=action
                )
                self.last_notify_time = current_time

        return login_success

        # Hàm có tác dụng tự động kiểm tra đổi ngôn ngữ hệ thống sang tiếng anh

    def click_check_cookie(self):
        try:
            btn = self.driver.find(".//*[@value='Allow all cookies']")
            if btn:
                btn.click()
        except Exception as e:
            print("Loi trong click_check_cookie: ", e)

    def check_and_set_english_locale(self):
        if self.driver.os_type_web:
            self.handle_check_and_set_english_locale_web()
        elif self.driver.os_type_mobile:
            self.handle_check_and_set_english_locale_mobile()

    def handle_check_and_set_english_locale_web(self):
        try:
            facebook = self.driver.find('//*[@id="facebook"]')
            if facebook is None:
                print('Không tìm thấy: //*[@id="facebook"]')
                return
            lang = facebook.get_attribute("lang")
            xpath_for_languages = {
                "vi": {
                    "setting": '//span[text() = "Cài đặt và quyền riêng tư"]',
                    "language": '//span[text() = "Ngôn ngữ"]',
                }
            }
            if lang == "en":
                return

            xpath_for_language = xpath_for_languages.get(lang, None)
            if xpath_for_language is None:
                print("Không tìm được ngôn ngữ phù hợp để đổi:", lang)
                return

            profile = self.driver.find(
                '(//*[@aria-expanded and @aria-label and @role="button"][1])[3]'
            )
            if profile is None:
                print("Không tìm thấy profile để click")
                return
            profile.click()
            sleep(3)

            setting = self.driver.find(xpath_for_language["setting"])
            if setting is None:
                print("Không tìm thấy setting để click")
                return
            setting.click()
            sleep(3)

            language = self.driver.find(xpath_for_language["language"])
            if language is None:
                print("Không tìm thấy language để click")
                return
            language.click()
            sleep(3)

            facebook_language = self.driver.find(
                '//div[@role="dialog"]//div[@role="list"]//div[@data-visualcompletion="ignore-dynamic" and @role="listitem"][2]'
            )
            if facebook_language is None:
                print("Không tìm thấy facebook_language để click")
                return
            facebook_language.click()

            # ⚡ Chờ input hiển thị thực sự
            input_box = self.driver.find('//div[@role="dialog"]//input')

            # ⚡ Focus vào input trước khi gõ
            self.driver.focus_element_script(input_box)
            input_box.clear()
            input_box.send_keys("UK")
            sleep(2)

            lang_en = self.driver.find(
                '//div[@role="dialog"]//ul[@role="listbox"]//li[1]'
            )
            if lang_en is None:
                print("Không tìm thấy lang_en để click")
                return
            lang_en.click()
            sleep(2)

        except Exception as e:
            print("Loi tai check noôn ngu:", e)

    def handle_check_and_set_english_locale_mobile(self):
        # check ngôn ngữ
        try:
            if self.check_login():
                self.driver.get("https://m.facebook.com/language/", e_wait=5)
                english = self.driver.find("//span[text() = 'English']")
                if english:
                    self.click_script(english)
                    sleep(20)
        except Exception as e:
            print("Loi tai check ngon ngu: ", e)
