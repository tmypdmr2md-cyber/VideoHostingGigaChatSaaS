# VideoFastAPI

FastAPI-приложение для загрузки и обработки видео с интеграцией внешних сервисов для хранения файлов, транскрибации и краткого суммирования контента.
<!-- 
https://youtu.be/SR5NYCdzKkc?si=sRZIyn5Bds74SYZR -->
на схемах остановились
<!-- 

 JSON is JavaScript Object Notation
 uv run uvicorn src.app:app --reload
 `http://127.0.0.1:8000/docs` -->


## Что умеет проект

- загружать и хранить медиафайлы через `ImageKit`
- работать как backend-сервис на `FastAPI`
- использовать внешние API для обработки видео и текста
- предоставлять интерактивную документацию Swagger

## Стек

- `FastAPI`
- `Uvicorn`
- `aiosqlite`
- `fastapi-users`
- `ImageKit`
- `python-dotenv`
- `uv`

## Структура проекта

```text
videoFastAPI/
├── main.py
├── pyproject.toml
├── README.md
├── uv.lock
└── src/
    └── app.py
```

## Быстрый старт

### 1. Клонирование и переход в проект

```bash
cd videoFastAPI
```

### 2. Установка зависимостей

Если используется `uv`:

```bash
uv sync
```

Если привычнее `venv` + `pip`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 3. Настройка переменных окружения

Создай файл `.env` в корне проекта и добавь туда необходимые переменные:

```env
IMAGEKIT_PRIVATE_KEY=your_private_key
IMAGEKIT_PUBLIC_KEY=your_public_key
IMAGEKIT_URL_ENDPOINT=https://ik.imagekit.io/your_id
IMAGEKIT_ID=your_id

GIGA_API=your_api_key
MAX_INPUT_LENGTH=12
```

## Запуск приложения

Через `uv`:

```bash
uv run uvicorn main:app --reload
```

Через активированное виртуальное окружение:

```bash
uvicorn main:app --reload
```

После запуска приложение будет доступно по адресу:

- `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Полезно знать

- `domain`, `endpoint` и `query params` относятся к URL-структуре запросов API
- для локальной разработки удобно использовать `--reload`
- секреты из `.env` не стоит коммитить в репозиторий

## Планы по развитию

- добавить описание API-эндпоинтов
- оформить `.env.example`
- описать сценарии загрузки и обработки видео
- добавить примеры запросов и ответов

## Пример URL

```text
http://site.ru/auth/developer?arr=123
```

Где:

- `site.ru` — домен
- `/auth/developer` — endpoint
- `arr=123` — query parameter
