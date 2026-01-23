from .model import Model

class Posts(Model):
    def __init__(self):
        super().__init__()
        self.table = 'posts'
    def add_post_newsfeed(self, data, params):
        return self.post("page-posts-newsfeed", data=data, params=params)