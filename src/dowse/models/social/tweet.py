from pydantic import BaseModel, Field


class Tweet(BaseModel):
    id: int
    content: str
    creator_id: int
    creator_name: str = Field(serialization_alias="caller")
