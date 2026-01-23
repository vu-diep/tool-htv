import re


class HandleCheckpoint:
    def __init__(self, driver):
        self.driver = driver

    def start(self):
        status = False
        code_check = 0
        try:
            current_url = self.driver.current_url
            match = re.search(r"checkpoint/(\d+)", current_url)
            if match:
                digits = match.group(1)
                last3 = digits[-3:]
                code_check = last3
                if int(last3) == 49:
                    if self.handle_checkpoint_049_captcha() == False:
                        status = True
                status = True
        except Exception as e:
            print("Loi trong handle_checkpoint:", e)
        return status, code_check

    def handle_checkpoint_049_captcha(self):
        from time import sleep

        try:
            dimiss = self.driver.find_element(
                "xpath", "//span[contains(text(),'Dimiss')]"
            )
            dimiss.click()
            sleep(10)
            return True
        except Exception as e:
            print("Loi trong handle_checkpoint_049_captcha: ", e)
        return False
