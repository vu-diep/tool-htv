from .model import Model
class Proxies(Model):

    def __init__(self):
        super().__init__()
        self.table = 'proxies'
    
    def show(self, id):
        return self.get(f"{self.table}/{id}")