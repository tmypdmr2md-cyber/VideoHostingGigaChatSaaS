from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .db import SubscriptionStatus, UserRole


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, examples=["alexander"])
    email: EmailStr = Field(..., examples=["alex@example.com"])
    password: str = Field(..., min_length=6, max_length=128, examples=["strong-password"])


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime


class UserMeResponse(UserResponse):
    has_active_subscription: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class FileCreateForm(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    is_free: bool = False


class FileUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    is_free: Optional[bool] = None


class FileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    uploader_id: UUID
    title: str
    description: Optional[str]
    original_name: str
    extension: str
    content_type: str
    size_bytes: int
    is_free: bool
    imagekit_url: str
    created_at: datetime
    updated_at: datetime


class FileDownloadResponse(BaseModel):
    url: str
    expires_in: int
    filename: str
    content_type: str


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    status: SubscriptionStatus
    plan_name: Optional[str]
    started_at: datetime
    expires_at: Optional[datetime]
    auto_renew: bool


class SubscriptionActivate(BaseModel):
    plan_name: str = Field(default="monthly", examples=["monthly"])
    days: int = Field(default=30, ge=1, le=365)
    auto_renew: bool = False
