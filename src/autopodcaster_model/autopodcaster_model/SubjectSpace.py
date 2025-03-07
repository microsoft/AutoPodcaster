from pydantic import BaseModel

class SubjectSpace(BaseModel):
    id: str
    subject: str
    date: str
    last_updated: str
    input_ids: list
    index_name: str