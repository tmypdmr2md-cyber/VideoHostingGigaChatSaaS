from collections.abc import AsyncGenerator
from datetime import datetime as dt
from datetime import datetime, timedelta
from enum import Enum
import os
import uuid
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    String,
    Text,
    Uuid,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")


class Base(DeclarativeBase):
    pass


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class SubscriptionStatus(str, Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    CANCELED = "canceled"
    EXPIRED = "expired"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(UserRole), default=UserRole.USER, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=dt.utcnow)

    subscription: Mapped[Optional["Subscription"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def has_active_subscription(self) -> bool:
        sub = self.subscription
        if sub is None or sub.status != SubscriptionStatus.ACTIVE:
            return False
        if sub.expires_at is not None and sub.expires_at < dt.utcnow():
            return False
        return True


class MediaFile(Base):
    __tablename__ = "media_files"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    uploader_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    extension: Mapped[str] = mapped_column(String(32), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    imagekit_file_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    imagekit_file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    imagekit_url: Mapped[str] = mapped_column(String(500), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    is_free: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=dt.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=dt.utcnow, onupdate=dt.utcnow
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        SqlEnum(SubscriptionStatus),
        default=SubscriptionStatus.INACTIVE,
        nullable=False,
    )
    plan_name: Mapped[Optional[str]] = mapped_column(String(100))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=dt.utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=lambda: dt.utcnow() + timedelta(days=30)
    )
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=dt.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=dt.utcnow, onupdate=dt.utcnow
    )

    user: Mapped["User"] = relationship(back_populates="subscription")


engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
