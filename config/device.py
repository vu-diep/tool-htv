import platform
import psutil
import socket
import requests
import uuid
import json

from utils.root import RootManager
from config.settings import Settings


class DeviceManager:
    def __init__(self):
        self.root = RootManager()

    def get_device_info(self):
        info = {}

        # MAC Address
        info["MAC"] = ":".join(
            [
                "{:02x}".format((uuid.getnode() >> ele) & 0xFF)
                for ele in range(0, 8 * 6, 8)
            ][::-1]
        )

        # CPU
        info["CPU"] = platform.processor()

        # Tên máy
        info["Tên máy"] = platform.node()

        # Kiến trúc hệ điều hành
        info["Kiến trúc"] = platform.architecture()[0]

        # Phiên bản Windows
        info["Phiên bản"] = platform.version()

        # Số lõi CPU
        info["Số lõi CPU"] = psutil.cpu_count(logical=True)

        # Hệ điều hành
        info["Hệ điều hành"] = platform.system() + " " + platform.release()

        # Địa chỉ IP cục bộ
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        info["Địa chỉ IP cục bộ"] = local_ip

        # Địa chỉ IP công khai và quốc gia
        try:
            public_ip = requests.get("https://api.ipify.org").text_content()
            info["Địa chỉ IP công khai"] = public_ip

            # Lấy thông tin quốc gia
            geo = requests.get(f"http://ip-api.com/json/{public_ip}").json()
            info["Quốc gia"] = {
                "name": geo.get("country"),
                "code": geo.get("countryCode"),
            }
        except:
            info["Địa chỉ IP công khai"] = "Không lấy được"
            info["Quốc gia"] = ""
        return info

    def create_dependencies(self):
        info = self.get_device_info()
        info["tool_version"] = Settings.version
        value_config_file = Settings.value_config_file
        value_config_file["systems_name"] = info["Tên máy"]
        self.root.create_file(
            "config.json", content=json.dumps(value_config_file, indent=4)
        )
