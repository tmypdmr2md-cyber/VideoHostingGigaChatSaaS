from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .db import MediaFile, User, get_db, init_db
from .schemas import (PostCreate, 
                      PostResponse, 
                      UserResponse)
import datetime as dt

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Создаем таблицы при старте приложения.
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)


# создание нового эндпоинта post для теста
@app.post("/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post: PostCreate, 
    session: AsyncSession = Depends(get_db)
) -> PostResponse:
    # Проверяем, что пост создается для существующего пользователя.
    owner = await session.get(User, post.owner_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Создаем ORM-объект для таблицы media_files.
    media_file = MediaFile(
        owner_id=post.owner_id,
        media_type=post.media_type,
        file_name=post.file_name,
        file_url=post.file_url,
        storage_key=post.storage_key,
        caption=post.caption,
    )

    # Сохраняем запись в базе и перечитываем ее, чтобы получить сгенерированные поля.
    session.add(media_file)
    await session.commit()
    await session.refresh(media_file)

    return media_file


# создание нового эндпоинта user для теста
@app.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
    name: str, 
    subscription_status: bool = False,
    created_at = dt.datetime.utcnow(),
    session: AsyncSession = Depends(get_db)
    ) -> UserResponse:

    # Вспомогательный эндпоинт для создания пользователей.
    user = User(name=name, subscription_status=subscription_status, created_at=created_at)
    session.add(user)

    await session.commit()
    await session.refresh(user)

    return {
        "id": user.id, 
        "name": user.name,
        "subscription_status": user.subscription_status,
        "created_at": user.created_at
        }
