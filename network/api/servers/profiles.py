from .model import Model

class Profiles(Model):

    def __init__(self):
        super().__init__()
        self.table = 'profiles'
        
    def show(self, id):
        return self.get(f"{self.table}/{id}")
    
    def create(self, data):
        return self.post(self.table, data=data)
    def update(self, id, data):
        return self.put(f"{self.table}/{id}", data=data)