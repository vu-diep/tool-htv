import requests
import logging

requests.packages.urllib3.util.connection.HAS_IPV6 = False
from utils.root import RootManager


class Model:
    def __init__(self):
        self.base_url = "https://htvtonghop.com/api"
        self.headers = {
            "X-CSRF-Token": "asfytechvudiepphattrien",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/json",
        }
        self.root = RootManager()

    def request(self, method, endpoint, params=None, data=None, files=None):
        config = self.root.get_content_file_config()
        self.headers["Systeam-Name"] = config.get("system_name")
        self.headers["Systeam-Id"] = config.get("system_id")
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.request(
                method=method,
                url=url,
                params=params,
                json=None if files else data,  # Dùng json nếu không có file
                data=data if files else None,  # Dùng data nếu có file
                files=files,
                headers=self.headers,
                timeout=180,
            )
            response.raise_for_status()
            return response.json()  # Trả về JSON nếu hợp lệ
        except ValueError:
            return response.text_content()  # Trả về text nếu JSON lỗi
        except requests.exceptions.HTTPError as err:

            try:
                e = err.response.json()  # Trả về JSON nếu hợp lệ
            except ValueError:
                e = err.response.text_content()  # Trả về text nếu JSON lỗi

            print(f"Request loi: {err}")
            return {"error": str(e)}  # Trả về lỗi thay vì chỉ in ra
        except requests.exceptions.RequestException as e:
            print(f"Request loi: {e}")
            return {"error": str(e)}

    def get(self, endpoint, params=None):
        return self.request("GET", endpoint, params=params)

    def post(self, endpoint, data=None, params=None, files=None):
        return self.request("POST", endpoint, data=data, params=params, files=files)

    def put(self, endpoint, data=None):
        return self.request("PUT", endpoint, data=data)

    def delete(self, endpoint, params=None):
        return self.request("DELETE", endpoint, params=params)
