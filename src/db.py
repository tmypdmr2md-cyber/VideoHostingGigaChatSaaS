from collections.abc import AsyncGenerator
from datetime import datetime as dt
from datetime import timedelta, datetime
from enum import Enum
import os
import uuid
from typing import Optional


from dotenv import load_dotenv
from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, String, Text, Uuid
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


load_dotenv()

# Если переменная окружения не задана, подключение не создастся.
DATABASE_URL = os.getenv("DATABASE_URL")


class Base(DeclarativeBase):
    # Общая база для всех ORM-моделей проекта.
    pass


class MediaType(str, Enum):
    # Ограничиваем типы загружаемого контента.
    PHOTO = "photo"
    VIDEO = "video"


class SubscriptionStatus(str, Enum):
    # Состояния подписки пользователя.
    INACTIVE = "inactive"
    ACTIVE = "active"
    CANCELED = "canceled"
    EXPIRED = "expired"


class User(Base):
    __tablename__ = "users"

    # Базовая таблица пользователей после аутентификации.
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=dt.utcnow)

    media_files: Mapped[list["MediaFile"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    subscription: Mapped[Optional["Subscription"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )


class MediaFile(Base):
    __tablename__ = "media_files"

    # Таблица хранит метаданные по фото и видео, а не сами бинарные файлы.
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    media_type: Mapped[MediaType] = mapped_column(SqlEnum(MediaType), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_key: Mapped[Optional[str]] = mapped_column(String(255))
    caption: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=dt.utcnow)

    owner: Mapped["User"] = relationship(back_populates="media_files")


class Subscription(Base):
    __tablename__ = "subscriptions"

    # У одного пользователя одна актуальная запись о подписке.
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
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


# Асинхронный движок и фабрика сессий для работы FastAPI с БД.
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    # Создаем все таблицы, описанные в Base.metadata.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    # Отдаем сессию в Depends(...), а после запроса корректно ее закрываем.
    async with AsyncSessionLocal() as session:
        yield session
