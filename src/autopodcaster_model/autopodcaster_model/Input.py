class Input:
    id: str
    title: str
    date: str
    last_updated: str
    status: str
    author: str = ''
    description: str = ''
    source: str
    type: str
    thumbnail_url: str = ''
    topics: list = []
    entities: list = []
    content: str = ''

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "date": self.date,
            "last_updated": self.last_updated,
            "status": self.status,
            "author": self.author,
            "description": self.description,
            "source": self.source,
            "type": self.type,
            "thumbnail_url": self.thumbnail_url,
            "topics": self.topics,
            "entities": self.entities,
            "content": self.content
        }
