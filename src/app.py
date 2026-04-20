import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import (
    create_access_token,
    get_current_user,
    hash_password,
    require_admin,
    verify_password,
)
from .db import (
    MediaFile,
    Subscription,
    SubscriptionStatus,
    User,
    UserRole,
    get_db,
    init_db,
)
from .schemas import (
    FileDownloadResponse,
    FileResponse,
    FileUpdate,
    SubscriptionActivate,
    SubscriptionResponse,
    TokenResponse,
    UserCreate,
    UserMeResponse,
    UserResponse,
)
from .storage import (
    delete_asset,
    generate_signed_url,
    upload_bytes,
)

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024 * 1024)))
SIGNED_URL_TTL = int(os.getenv("SIGNED_URL_TTL", "300"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="VideoFastAPI",
    description=(
        "Подписочный файлохостинг одного автора. "
        "Хранение — ImageKit, аутентификация — JWT, контроль доступа — роли + подписка."
    ),
    lifespan=lifespan,
)


# ---------- AUTH ----------

@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate,
    session: AsyncSession = Depends(get_db),
) -> User:
    existing = await session.scalar(
        select(User).where(
            (User.username == payload.username) | (User.email == payload.email)
        )
    )
    if existing is not None:
        raise HTTPException(status_code=400, detail="Username or email already taken")

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.USER,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@app.post("/auth/login", response_model=TokenResponse)
async def login(
    username: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user = await session.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is disabled")
    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)


@app.get("/auth/me", response_model=UserMeResponse)
async def me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserMeResponse:
    await session.refresh(user, attribute_names=["subscription"])
    return UserMeResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        has_active_subscription=user.has_active_subscription(),
    )


# ---------- FILES: ADMIN MANAGEMENT ----------

@app.post(
    "/files",
    response_model=FileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_file(
    title: str = Form(...),
    description: Optional[str] = Form(default=None),
    is_free: bool = Form(default=False),
    upload: UploadFile = File(...),
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> MediaFile:
    original_name = upload.filename or "unnamed"
    extension = Path(original_name).suffix.lstrip(".").lower()
    content_type = upload.content_type or "application/octet-stream"

    data = await upload.read()
    await upload.close()
    size = len(data)
    if size == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if size > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large")

    try:
        asset = await asyncio.to_thread(
            upload_bytes,
            data,
            original_name,
            True,
            [f"is_free:{str(is_free).lower()}", f"ext:{extension or 'bin'}"],
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ImageKit upload failed: {exc}")

    media = MediaFile(
        uploader_id=admin.id,
        title=title,
        description=description,
        original_name=original_name,
        extension=extension,
        content_type=content_type,
        imagekit_file_id=asset.file_id,
        imagekit_file_path=asset.file_path,
        imagekit_url=asset.url,
        size_bytes=asset.size_bytes or size,
        is_free=is_free,
    )
    session.add(media)
    await session.commit()
    await session.refresh(media)
    return media


@app.patch("/files/{file_id}", response_model=FileResponse)
async def update_file(
    file_id: uuid.UUID,
    payload: FileUpdate,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> MediaFile:
    media = await session.get(MediaFile, file_id)
    if media is None:
        raise HTTPException(status_code=404, detail="File not found")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(media, key, value)
    await session.commit()
    await session.refresh(media)
    return media


@app.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: uuid.UUID,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> None:
    media = await session.get(MediaFile, file_id)
    if media is None:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        await asyncio.to_thread(delete_asset, media.imagekit_file_id)
    except Exception:
        # Не блокируем удаление записи из БД из-за ошибки в ImageKit —
        # админ сможет дочистить в панели.
        pass

    await session.delete(media)
    await session.commit()


# ---------- FILES: LISTING & DOWNLOAD ----------

def _can_access(user: User, media: MediaFile) -> bool:
    if user.is_admin:
        return True
    if media.is_free:
        return True
    return user.has_active_subscription()


@app.get("/files", response_model=list[FileResponse])
async def list_files(
    only_free: bool = Query(default=False),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[MediaFile]:
    await session.refresh(user, attribute_names=["subscription"])

    stmt = select(MediaFile).order_by(MediaFile.created_at.desc())
    if not user.is_admin and not user.has_active_subscription():
        stmt = stmt.where(MediaFile.is_free.is_(True))
    elif only_free:
        stmt = stmt.where(MediaFile.is_free.is_(True))

    result = await session.scalars(stmt)
    return list(result.all())


@app.get("/files/{file_id}", response_model=FileResponse)
async def get_file_metadata(
    file_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MediaFile:
    await session.refresh(user, attribute_names=["subscription"])
    media = await session.get(MediaFile, file_id)
    if media is None:
        raise HTTPException(status_code=404, detail="File not found")
    if not _can_access(user, media):
        raise HTTPException(status_code=403, detail="Subscription required")
    return media


@app.get("/files/{file_id}/download", response_model=FileDownloadResponse)
async def download_file(
    file_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> FileDownloadResponse:
    await session.refresh(user, attribute_names=["subscription"])
    media = await session.get(MediaFile, file_id)
    if media is None:
        raise HTTPException(status_code=404, detail="File not found")
    if not _can_access(user, media):
        raise HTTPException(status_code=403, detail="Subscription required")

    try:
        signed_url = await asyncio.to_thread(
            generate_signed_url, media.imagekit_file_path, SIGNED_URL_TTL
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ImageKit URL error: {exc}")

    return FileDownloadResponse(
        url=signed_url,
        expires_in=SIGNED_URL_TTL,
        filename=media.original_name,
        content_type=media.content_type,
    )


# ---------- SUBSCRIPTIONS ----------

@app.get("/subscriptions/me", response_model=Optional[SubscriptionResponse])
async def my_subscription(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Optional[Subscription]:
    await session.refresh(user, attribute_names=["subscription"])
    return user.subscription


@app.post("/subscriptions/activate", response_model=SubscriptionResponse)
async def activate_subscription(
    payload: SubscriptionActivate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Subscription:
    """Ручная активация подписки. Будет заменена callback'ом платёжного шлюза."""
    await session.refresh(user, attribute_names=["subscription"])
    sub = user.subscription
    now = datetime.utcnow()
    expires = now + timedelta(days=payload.days)

    if sub is None:
        sub = Subscription(
            user_id=user.id,
            status=SubscriptionStatus.ACTIVE,
            plan_name=payload.plan_name,
            started_at=now,
            expires_at=expires,
            auto_renew=payload.auto_renew,
        )
        session.add(sub)
    else:
        sub.status = SubscriptionStatus.ACTIVE
        sub.plan_name = payload.plan_name
        sub.started_at = now
        sub.expires_at = expires
        sub.auto_renew = payload.auto_renew

    await session.commit()
    await session.refresh(sub)
    return sub


@app.post("/subscriptions/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Subscription:
    await session.refresh(user, attribute_names=["subscription"])
    sub = user.subscription
    if sub is None:
        raise HTTPException(status_code=404, detail="No subscription to cancel")
    sub.status = SubscriptionStatus.CANCELED
    sub.auto_renew = False
    await session.commit()
    await session.refresh(sub)
    return sub


# ---------- ADMIN BOOTSTRAP ----------

@app.post("/admin/bootstrap", response_model=UserResponse, include_in_schema=False)
async def bootstrap_admin(
    payload: UserCreate,
    secret: str = Query(..., description="Должен совпадать с ADMIN_BOOTSTRAP_SECRET"),
    session: AsyncSession = Depends(get_db),
) -> User:
    expected = os.getenv("ADMIN_BOOTSTRAP_SECRET")
    if not expected or secret != expected:
        raise HTTPException(status_code=403, detail="Forbidden")

    existing_admin = await session.scalar(
        select(User).where(User.role == UserRole.ADMIN)
    )
    if existing_admin is not None:
        raise HTTPException(status_code=400, detail="Admin already exists")

    admin = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.ADMIN,
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)
    return admin
