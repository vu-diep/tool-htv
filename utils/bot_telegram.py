import requests
import logging
from telegram import Bot
requests.packages.urllib3.util.connection.HAS_IPV6 = False

class BotTelegram:
    def __init__(self, token):
        self.token = token
        self.bot = Bot(token)
    
    def createChat(self):
        url = f'https://api.telegram.org/bot{self.token}/getUpdates'
        response = requests.get(url)
        data = response.json()
        
        # Xử lý nếu response không trả về 'result'
        if 'result' not in data:
            print("Không tìm thấy trường 'result' trong API response.")
            self.chat_ids = []
            return self

        chat_ids = set()
        for chat in data['result']:
            if 'message' in chat and 'chat' in chat['message']:
                chat_id = chat['message']['chat']['id']
                chat_ids.add(chat_id)
        self.chat_ids = list(chat_ids)
        return self
    
    def get_chat_list(self):
        """Lấy danh sách các cuộc trò chuyện từ getUpdates"""
        url = f'https://api.telegram.org/bot{self.token}/getUpdates'
        response = requests.get(url)
        data = response.json()
        if 'result' not in data:
            print("Không tìm thấy trường 'result' trong API response.")
            return []

        chats = {}
        for item in data['result']:
            if 'message' in item and 'chat' in item['message']:
                chat = item['message']['chat']
                chat_id = chat.get('id')
                title = chat.get('title') or chat.get('username') or f"{chat.get('first_name', '')} {chat.get('last_name', '')}".strip()
                chats[chat_id] = title or f"Chat {chat_id}"
        
        return [{"chat_id": chat_id, "title": title} for chat_id, title in chats.items()]

    async def send_messages(self, chat_id, message=''):
        await self.bot.send_message(chat_id=chat_id, text=message)
        logging.info(f"Đã gửi tin nhắn tới chat_id: {chat_id}")