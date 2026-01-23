from .model import Model
class Jobs(Model):
    def __init__(self):
        super().__init__()
        self.table = "jobs"

    def update(self, id, data):
        url = f"{self.table}/{id}"
        return self.put(url, data=data)

    def registration_check_wall(self, data):
        url = f"{self.table}/registration-check-wall"
        return self.post(url, data=data)

    def delete_mutile(self, ids):
        url = f"{self.table}/delete-mutile"
        return self.post(url, {"ids": ids})
