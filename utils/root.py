import os
import sys
import json

from config.settings import settings
class RootManager:
    def get_root(self):
        current_exe = sys.executable
        root = os.path.dirname(current_exe)
        if settings.status_tool in  ["development", "test"]:
            root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return root
    
    def get_full_url_user(self, file_name):
        # Lấy đường dẫn thư mục người dùng, ví dụ: C:\Users\TenUser
        user_dir = self.get_root()
        # Ghép đường dẫn và chuẩn hóa lại
        file_path = os.path.join(user_dir, file_name)
        # Làm phẳng (chuẩn hóa) đường dẫn
        file_path = os.path.abspath(os.path.normpath(file_path))
        return file_path
    
    def create_file(self, file_name, content, mode='w+'):
        file_path = self.get_full_url_user(file_name=file_name)
        try:
            # Ghi nội dung vào file (nếu chưa có thì tạo file)
            with open(file_path, mode, encoding="utf-8") as f:
                f.write(content + "\n")
        except Exception as log_err:
            print("Khong the ghi file:", log_err)
        return file_path
    
    def get_content_file_config(self, key=None, default_value=None):
        # kiểm tra và tạo file nếu nó chưa tồn tại
        config_path = self.get_full_url_user("config.json")
        # Đọc file sau khi tạo
        try:
            with open(config_path, "r", encoding="utf-8") as config_file:
                settings = json.load(config_file)
        except Exception as e:
            print(f"Loi khi doc file file setting: {e}")
            return default_value  # Trả về giá trị mặc định nếu có lỗi
        return settings if key is None else settings.get(key, default_value)
    
    def config_message(self, message, action):
        name_pc = self.get_content_file_config('systems_name')
        content = (
            f"🔔 **Thông Báo**\n"
            f"🖥️ Máy: {name_pc}\n"
            f"🧩 Phiên bản: {settings.version}\n"
            f"⚙️ Chức năng: {action}\n"
            f"📝 Nội dung: {message}"
        )
        return content