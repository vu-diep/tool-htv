# config/settings.py
class Settings:
    # lưu trạng thái của tool.
    # development: Chế độ phát triển
    # test: Chế độ test, gần giống với xây dựng
    # build: Chế độ xây dựng
    status_tool = "development"
    value_config_file = {
        "driver": {
            "headless": "false",
            "omocaptcha_token": "OMO_YPTPQ1NI1ECAKCDU0XEKQIGXS4ZAYIAKDKT4MPGKQOGGT3KGFZMZO7XYHL1CDU1738834769",
            "chat_telegram_id_tool_fb_success": "-1002493389024",
            "chat_telegram_id_tool_fb_check": "-1002448273317",
        },
        "systems_id": 0,
        "systems_name": "",
    }
    version = "1_8_2"
    name = "main"
    current_version = f"{name}.exe"
    chromium_path = "E:/asfy/facebook/tool_playwright/resources/chrome/chrome-win/chrome.exe"
    extention_omocapcha_path = "E:/asfy/facebook/tool_playwright/resources/extensions/omocaptcha-chrome_v1.2.7"

settings = Settings()
