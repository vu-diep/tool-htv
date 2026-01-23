from .model import Model

class ToolActivityLog(Model):
    def __init__(self):
        super().__init__()
        self.table = 'tool-activity-log'

    def update(self, id, data):
        url = f"{self.table}/{id}"
        return self.put(url, data=data)
    def create(self, data):
        url = f"{self.table}"
        return self.post(url, data=data)