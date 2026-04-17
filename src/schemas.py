from pydantic import BaseModel, Field

class PostCreate(BaseModel):
    title: str
    content: str