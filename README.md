# VideoFastAPI

Подписочный файлохостинг одного автора на FastAPI.
Автор (админ) загружает материалы — видео, PDF, документы, ноутбуки, код, архивы — а пользователи получают к ним доступ: часть файлов помечена как «бесплатные» и доступна всем зарегистрированным, остальное открывается только по активной подписке.

Бинарники хранятся в **ImageKit** (как приватные ассеты), доступ к ним выдаётся через подписанные URL с ограниченным временем жизни. Подписочный модуль сейчас работает как заглушка — позже подключится интернет-эквайринг.

---

## Оглавление

- [Архитектура](#архитектура)
- [Роли и модель доступа](#роли-и-модель-доступа)
- [Стек](#стек)
- [Структура проекта](#структура-проекта)
- [Переменные окружения](#переменные-окружения)
- [Быстрый старт](#быстрый-старт)
- [API-справочник](#api-справочник)
- [Сценарии использования](#сценарии-использования)
- [Модели данных](#модели-данных)
- [Безопасность и замечания](#безопасность-и-замечания)
- [Дорожная карта](#дорожная-карта)

---

## Архитектура

```
┌──────────┐   JWT    ┌──────────────┐   upload/delete   ┌──────────┐
│  Client  │ ───────► │   FastAPI    │ ────────────────► │ ImageKit │
│ (admin/  │ ◄─────── │  app (src/)  │ ◄──── signed URL ─│          │
│  user)   │          └──────┬───────┘                   └──────────┘
└──────────┘                 │ SQLAlchemy async
                             ▼
                        ┌──────────┐
                        │  SQLite  │  (users, media_files, subscriptions)
                        └──────────┘
```

- Пароли хешируются через `bcrypt`, токены — JWT (HS256, `PyJWT`).
- Загружаемые файлы читаются в память и отправляются в ImageKit как `is_private_file=True`. Локально на диске ничего не лежит.
- Скачивание проходит через эндпоинт, который проверяет права и возвращает клиенту signed URL с TTL (по умолчанию 5 минут).
- Удаление из БД пытается одновременно удалить ассет в ImageKit (ошибка ImageKit не блокирует удаление записи).

## Роли и модель доступа

| Роль                     | Источник                                 | Может смотреть          | Может качать            | Может загружать/править/удалять |
| ------------------------ | ---------------------------------------- | ----------------------- | ----------------------- | ------------------------------- |
| **admin**                | `User.role == ADMIN`                     | все файлы               | все файлы               | да                              |
| **подписчик**            | `User.role == USER` + активная `Subscription` | все файлы          | все файлы               | нет                             |
| **пользователь без подписки** | `User.role == USER`, нет активной подписки | только `is_free=true` | только `is_free=true`   | нет                             |

«Активная» подписка = `status == ACTIVE` и `expires_at` в будущем (либо `NULL`).

Назначение роли `ADMIN` невозможно через публичный API — только через одноразовый эндпоинт `POST /admin/bootstrap`, защищённый общим секретом.

## Стек

- `FastAPI` + `Uvicorn`
- `SQLAlchemy 2.x` (async) + `aiosqlite`
- `Pydantic v2` (+ `email-validator`)
- `bcrypt` для паролей, `PyJWT` для токенов
- `python-multipart` для multipart-загрузки
- `imagekitio` SDK для хранилища

## Структура проекта

```text
videoFastAPI/
├── main.py                 # точка входа (uvicorn)
├── pyproject.toml
├── README.md
├── test.db                 # SQLite (создаётся автоматически)
└── src/
    ├── app.py              # роуты FastAPI
    ├── auth.py             # JWT, bcrypt, зависимости get_current_user / require_admin
    ├── db.py               # SQLAlchemy-модели и движок
    ├── schemas.py          # Pydantic-схемы запросов/ответов
    └── storage.py          # обёртка над ImageKit SDK
```

## Переменные окружения

`.env` в корне проекта:

```env
# База данных
DATABASE_URL=sqlite+aiosqlite:///./test.db

# Аутентификация
SECRET_KEY=<token_urlsafe(64)>            # для подписи JWT
ACCESS_TOKEN_EXPIRE_MINUTES=60
ADMIN_BOOTSTRAP_SECRET=<token_urlsafe(32)># одноразовый секрет для создания первого админа

# Хранилище (ImageKit)
IMAGEKIT_PRIVATE_KEY=private_...
IMAGEKIT_PUBLIC_KEY=public_...
IMAGEKIT_URL_ENDPOINT=https://ik.imagekit.io/<your_id>
IMAGEKIT_ID=<your_id>
IMAGEKIT_FOLDER=/videoFastAPI              # папка внутри ImageKit
SIGNED_URL_TTL=300                         # TTL подписанных ссылок, сек
MAX_UPLOAD_BYTES=5368709120                # 5 GB; значение в БАЙТАХ
```

Сгенерировать секреты:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Быстрый старт

```bash
cd videoFastAPI
uv sync                    # или: python -m venv .venv && source .venv/bin/activate && pip install -e .
cp .env.example .env       # если есть, иначе создай вручную из секции выше
uv run python main.py      # или: uvicorn src.app:app --reload
```

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc:      `http://127.0.0.1:8000/redoc`

**Первый запуск:** создай админа через `POST /admin/bootstrap?secret=<ADMIN_BOOTSTRAP_SECRET>` (эндпоинт скрыт из Swagger). Второй раз он не сработает.

## API-справочник

Все защищённые маршруты требуют заголовок `Authorization: Bearer <access_token>`, полученный через `/auth/login`.

### Аутентификация

| Метод | Путь              | Доступ    | Назначение                                |
| ----- | ----------------- | --------- | ----------------------------------------- |
| POST  | `/auth/register`  | публично  | Регистрация обычного пользователя         |
| POST  | `/auth/login`     | публично  | Вход, возвращает JWT (OAuth2 password flow) |
| GET   | `/auth/me`        | авторизо­ванный | Профиль + флаг активной подписки     |

`/auth/login` принимает `application/x-www-form-urlencoded` с полями `username`, `password`.

### Файлы

| Метод  | Путь                          | Доступ          | Назначение                                    |
| ------ | ----------------------------- | --------------- | --------------------------------------------- |
| POST   | `/files`                      | admin           | Загрузка файла (`multipart/form-data`)        |
| GET    | `/files`                      | авторизованный  | Список файлов (фильтруется по правам)         |
| GET    | `/files/{id}`                 | авторизованный* | Метаданные одного файла                       |
| PATCH  | `/files/{id}`                 | admin           | Изменить `title`, `description`, `is_free`    |
| DELETE | `/files/{id}`                 | admin           | Удалить файл (и ассет в ImageKit)             |
| GET    | `/files/{id}/download`        | авторизованный* | Получить подписанный URL к файлу              |

`*` — при условии, что файл помечен `is_free=true` или у пользователя активная подписка; иначе `403`.

**Загрузка** (`POST /files`) — поля формы:

| Поле          | Тип      | Обязательно | Примечание                     |
| ------------- | -------- | ----------- | ------------------------------ |
| `title`       | string   | да          | Отображаемое имя               |
| `description` | string   | нет         | Произвольное описание          |
| `is_free`     | bool     | нет (default `false`) | Флаг бесплатного контента |
| `upload`      | file     | да          | Сам файл                       |

Ограничение размера — `MAX_UPLOAD_BYTES`. Поддерживаются любые типы файлов: `.mp4`, `.pdf`, `.docx`, `.xlsx`, `.py`, `.ipynb`, `.db`, `.zip` и т.д. Тип определяется по `Content-Type` и расширению.

**Ответ на скачивание:**

```json
{
  "url": "https://ik.imagekit.io/<id>/videoFastAPI/file.mp4?ik-t=...&ik-s=...",
  "expires_in": 300,
  "filename": "lecture-01.mp4",
  "content_type": "video/mp4"
}
```

Клиент должен перейти по `url` в течение `expires_in` секунд.

### Подписки

| Метод | Путь                         | Доступ         | Назначение                              |
| ----- | ---------------------------- | -------------- | --------------------------------------- |
| GET   | `/subscriptions/me`          | авторизованный | Текущая подписка (или `null`)           |
| POST  | `/subscriptions/activate`    | авторизованный | **Заглушка**: активирует подписку сразу |
| POST  | `/subscriptions/cancel`      | авторизованный | Переводит подписку в `CANCELED`         |

`/subscriptions/activate` принимает JSON:

```json
{"plan_name": "monthly", "days": 30, "auto_renew": false}
```

Реальный платёжный шлюз заменит эту ручку: вместо прямой активации придёт callback об успешной оплате.

### Админ-bootstrap

| Метод | Путь                | Доступ             | Назначение                             |
| ----- | ------------------- | ------------------ | -------------------------------------- |
| POST  | `/admin/bootstrap`  | по query-секрету   | Создаёт первого админа (однократно)    |

Пример: `POST /admin/bootstrap?secret=<ADMIN_BOOTSTRAP_SECRET>` с телом `UserCreate`.

## Сценарии использования

**1. Поднять проект и завести админа**

```bash
curl -X POST "http://127.0.0.1:8000/admin/bootstrap?secret=<BOOTSTRAP>" \
  -H "Content-Type: application/json" \
  -d '{"username":"author","email":"author@site.ru","password":"very-strong"}'
```

**2. Логин и получение токена**

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -d "username=author&password=very-strong"
# → {"access_token":"<JWT>","token_type":"bearer"}
```

**3. Загрузка файла админом**

```bash
curl -X POST http://127.0.0.1:8000/files \
  -H "Authorization: Bearer $TOKEN" \
  -F "title=Лекция 1" \
  -F "description=Вводная" \
  -F "is_free=true" \
  -F "upload=@./lecture-01.mp4"
```

**4. Обычный пользователь получает список и скачивает**

```bash
curl http://127.0.0.1:8000/files -H "Authorization: Bearer $USER_TOKEN"
curl http://127.0.0.1:8000/files/<id>/download -H "Authorization: Bearer $USER_TOKEN"
# → signed URL; его открываем в браузере/качаем через wget
```

**5. Активация подписки (сейчас — вручную, потом — через эквайринг)**

```bash
curl -X POST http://127.0.0.1:8000/subscriptions/activate \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plan_name":"monthly","days":30}'
```

## Модели данных

**User** — `users`

| поле            | тип       | прим.                                |
| --------------- | --------- | ------------------------------------ |
| `id`            | UUID (PK) |                                      |
| `username`      | str (uniq)|                                      |
| `email`         | str (uniq)|                                      |
| `password_hash` | str       | bcrypt                               |
| `role`          | enum      | `admin` / `user`                     |
| `is_active`     | bool      |                                      |
| `created_at`    | datetime  |                                      |

**MediaFile** — `media_files`

| поле                 | тип       | прим.                                 |
| -------------------- | --------- | ------------------------------------- |
| `id`                 | UUID (PK) |                                       |
| `uploader_id`        | UUID (FK) | ссылка на `users.id`                  |
| `title`              | str       |                                       |
| `description`        | text?     |                                       |
| `original_name`      | str       | исходное имя файла при загрузке       |
| `extension`          | str       | `mp4`, `pdf`, `ipynb`, ...            |
| `content_type`       | str       | MIME                                  |
| `imagekit_file_id`   | str (uniq)| ID ассета в ImageKit (для удаления)   |
| `imagekit_file_path` | str       | путь в ImageKit (для signed URL)      |
| `imagekit_url`       | str       | базовый URL ассета                    |
| `size_bytes`         | bigint    | размер (возвращает ImageKit)          |
| `is_free`            | bool      | доступен без подписки                 |
| `created_at`/`updated_at` | datetime |                                  |

**Subscription** — `subscriptions` (1:1 к User)

| поле          | тип       | прим.                                                      |
| ------------- | --------- | ---------------------------------------------------------- |
| `id`          | UUID (PK) |                                                            |
| `user_id`     | UUID (uniq, FK) |                                                      |
| `status`      | enum      | `inactive` / `active` / `canceled` / `expired`             |
| `plan_name`   | str?      |                                                            |
| `started_at`  | datetime  |                                                            |
| `expires_at`  | datetime? | если `< now()` — подписка считается истёкшей               |
| `auto_renew`  | bool      |                                                            |
| `created_at`/`updated_at` | datetime |                                                |

## Безопасность и замечания

- **JWT** подписан `SECRET_KEY`. Утечка ключа = возможность выпускать токены от имени любого пользователя. Храни в секрете, для продакшна — выноси в секрет-менеджер.
- **ADMIN_BOOTSTRAP_SECRET** нужен только один раз. После создания админа убери переменную из окружения.
- **ImageKit-ассеты приватные** (`is_private_file=true`), прямой URL без подписи не отдаёт контент. Signed URL имеет TTL (`SIGNED_URL_TTL`) — держи его минимальным (минуты, не часы).
- **Загрузка в память:** текущая реализация читает файл в RAM целиком перед отправкой в ImageKit. Для больших видео это нормально на MVP-этапе; при росте трафика перейдём на стриминг / прямую загрузку с клиента по upload-токену ImageKit.
- **`MAX_UPLOAD_BYTES` — в байтах.** Для 500 MB — `524288000`, для 2 GB — `2147483648`. Не ставь туда мегабайты.
- **Миграции:** сейчас таблицы создаются через `Base.metadata.create_all` при старте. Как только схема стабилизируется — подключи Alembic.

## Дорожная карта

- [ ] Интеграция интернет-эквайринга (ЮKassa / Stripe) в `POST /subscriptions/activate`.
- [ ] Прямая загрузка из браузера в ImageKit через `upload token` (минует наш сервер).
- [ ] Фоновая задача по переводу подписок в `EXPIRED` после `expires_at`.
- [ ] Пагинация и поиск в `GET /files`.
- [ ] Alembic-миграции.
- [ ] Rate limiting и CORS-настройки для прод-домена.
- [ ] Плейлисты / коллекции видео.
- [ ] Фронтенд (SPA) поверх API.
