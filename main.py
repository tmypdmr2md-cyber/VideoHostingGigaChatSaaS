import os
import dotenv
import uvicorn
from src.app import *

# python main.py

def main ():
    pass 

if __name__ == "__main__":
    # Запускаем FastAPI-приложение через Uvicorn в режиме локальной разработки.
    uvicorn.run("src.app:app", host="127.0.0.1", port=8000, reload=True)
    main()
