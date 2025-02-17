from pydantic import BaseModel


class Tweet(BaseModel):
    id: int
    content: str
    creator_id: int
    creator_name: str
