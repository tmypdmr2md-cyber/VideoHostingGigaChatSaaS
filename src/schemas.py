from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .db import MediaType


class PostCreate(BaseModel):
    # Схема тела запроса при создании записи о медиафайле.
    owner_id: UUID
    media_type: MediaType = Field(..., examples=["video"])
    file_name: str = Field(..., examples=["demo.mp4"])
    file_url: str = Field(..., examples=["https://cdn.example.com/demo.mp4"])
    storage_key: str | None = Field(default=None, examples=["media/demo.mp4"])
    caption: str | None = Field(default=None, examples=["Первое загруженное видео"])


class PostResponse(BaseModel):
    # from_attributes=True позволяет строить ответ прямо из ORM-объекта SQLAlchemy.
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    media_type: MediaType
    file_name: str
    file_url: str
    storage_key: str | None
    caption: str | None
    created_at: datetime

class UserResponse(BaseModel):
    # from_attributes=True позволяет строить ответ прямо из ORM-объекта SQLAlchemy.
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    subcription_status: bool
    created_at: datetime
