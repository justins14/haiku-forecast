from typing import List, Dict
from .haikus import haikus, build_tag_index

class HaikuManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.init_haikus()
        return cls._instance
    
    def init_haikus(self):
        self.haikus = haikus
        self.tag_index = self.build_tag_index()
    
    def build_tag_index(self) -> Dict[str, List[str]]:
        return build_tag_index(self.haikus)
    
    def get_haikus_by_tags(self, tags: List[str]) -> List[Dict]:
        """
        Retrieve haikus that match any of the given tags.
        """
        matching_haiku_ids = set()
        for tag in tags:
            if tag in self.tag_index:
                matching_haiku_ids.update(self.tag_index[tag])
        
        return [self.haikus[haiku_id] for haiku_id in matching_haiku_ids]