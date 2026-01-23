from .model import Model

class Account(Model):
    def __init__(self):
        super().__init__()
        self.table = 'accounts'
    
    def show(self ,id):
        url = f"{self.table}/{id}"
        return self.get(url)
    
    def update(self, id, data):
        url = f"{self.table}/{id}"
        return self.put(url, data=data)
    
    def add(self, data):
        url = f"{self.table}"
        return self.post(url, data=data)
    
    def get_keywords(self, account_id, get_all=False):
        url = f"{self.table}/keywords/{account_id}"
        return self.get(url, params={
            'get_all': get_all
        })
