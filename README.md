# VIDEO SHARING APP

http://site.ru/auth/developer?arr=123

site.ru -- Domain

auth/developer - endpoint

arr=123 - query parametr

Запуск FAST_API приложения

 uvicorn copykit_api:app --reload
 http://127.0.0.1:8000/docs



# VideoGeneration — файлообменник с интегрированным ChatGPT для транскрибации видео и суммирования материала, а также сохранения на видео хостинге



## 🚀 Быстрый старт

Команда для инициализации проекта
uv init .



### Локальная разработка

```bash
# Создать виртуальное окружение
python3.12 -m venv venv

# Активировать окружение
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Скопировать .env.example в .env и заполнить
cp .env.example .env
# Отредактируй .env и добавь свой GIGA_API ключ

# Запустить сервер (режим разработки)
fastapi dev

# Или напрямую через uvicorn
uvicorn app.copykit_api:app --reload
```

Интерактивная документация доступна: **http://127.0.0.1:8000/docs**

### API Эндпоинты


add gitignor main.py 