from .model import Model

class Pages(Model):
    def __init__(self):
        super().__init__()
        self.table = 'pages'
        
    def get_all(self, params = None):
        return self.get(self.table, params=params)
    
    def show(self ,id):
        url = f"{self.table}/{id}" 
        return self.get(url)

    def get_page_crawl(self, data = []):
        return self.post(f"{self.table}/get-page-crawl", data=data)
    
    def update(self, id, data):
        return self.put(f"pages/api/{id}", data=data)
