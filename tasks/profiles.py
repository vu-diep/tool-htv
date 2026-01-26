from time import sleep

from network.api.servers.profiles import Profiles as ProfilesNetwork
from state.session import session_profiles

# from main import socket_server
from browser.driver import Driver


class Profiles:
    def __init__(self):
        self.id = 0
        self.profiles = ProfilesNetwork()

    def start(self, id):
        profile = self.profiles.show(id)
        stop_event = session_profiles[id]["stop_event"]
        driver = None
        user_closed_browser = False

        try:
            driver = Driver(profile=profile, headless=False)
            driver.get('https://www.facebook.com/m.mmy.s.n.2025/posts/pfbid02q2Lw5Gs2A7vWeyav7ZXZob7EPv5ecjez9A1sAc2ws618DRE1vGEQEzpfnPpYoS4ql')
            self.socket_profile(id, status="Đã khởi tạo trình duyệt", check=1)

            while not stop_event.is_set():
                sleep(1)

        except Exception as e:
            print("loi khi khoi tao profile: ", e)

        finally:
            # ⚠️ finally LUÔN chạy, nhưng xử lý KHÁC NHAU

            if driver and not user_closed_browser:
                # 👉 chỉ quit khi SERVER yêu cầu
                print("Server chu dong dong browser")
                driver.quit()

            if not user_closed_browser:
                self.socket_profile(id, status="Trình duyệt đang bị dừng", check=2)
                session_profiles.pop(str(id), None)

    def close(self, id):
        print("Tao process dung trinh duyet")

        data = session_profiles.get(str(id))
        if not data:
            return

        self.socket_profile(id, status="Đã đóng trình duyệt", check=2)
        del session_profiles[str(id)]

    def socket_profile(self, id,  status, check=None, status_process=None):
        data = {
            "id": id,
            "status": status,
            "status_process": status_process,
        }
        if check is not None:
            data["check"] = check
        session_profiles[str(id)] = {**session_profiles.get(str(id), {}), **data}
        # socket_server.emit("profiles_status", {"data": data}, namespace="/")
