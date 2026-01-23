from .model import Model

class Histories(Model):
    def create(self, data):
        res = self.post("history-crawl-page", data=data)
        return res
    def createNewsFeed(self, data):
        res = self.post("insert-history-crawl-newfeed", data=data)
        return res
    def insert_craw_article_website(self, data):
        res = self.post("insert-craw-article-website", data=data)
        return res
    def update_craw_article_website(self, id, data):
        res = self.put(f"update-craw-article-website/{id}", data=data)
        return res
    
    def updateValidCrawlNewsFeed(self, id, data):
        return self.put(f"update-valid-history-crawl-newfeed/{id}", data=data)
    def update(self, id, data):
        return self.put(f"history-crawl-page/{id}", data=data)
    
    def update_count(self, history_id, data):
            return self.post(f"history-crawl-update-count/{history_id}", data=data)
