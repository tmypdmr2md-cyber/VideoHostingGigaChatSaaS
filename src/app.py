from fastapi import FastAPI, HTTPException
import os
import dotenv
from .schemas import PostCreate as Post
from gigachat import GigaChat

dotenv.load_dotenv()

IMAGEKIT_PRIVATE_KEY=os.getenv("IMAGEKIT_PRIVATE_KEY")
IMAGEKIT_PUBLIC_KEY=os.getenv("IMAGEKIT_PUBLIC_KEY")
IMAGEKIT_URL_ENDPOINT=os.getenv("IMAGEKIT_URL_ENDPOINT")
IMAGEKIT_ID=os.getenv("IMAGEKIT_ID")
GIGA_API=os.getenv("GIGA_API")
MAX_INPUT_LENGTH=os.getenv("MAX_INPUT_LENGTH")

app = FastAPI()

# JSON is JavaScript Object Notation
# uv run uvicorn src.app:app --reload
# `http://127.0.0.1:8000/docs`

# src.app (это название папки):app(это названиие переменной app = FastAPI())

text_posts = {
    1: {"title": "First Post", "content": "This is the first post"},
    2: {"title": "Second Post", "content": "This is the second post"},
    3: {"title": "Third Post", "content": "This is the third post"},
    4: {"title": "Fourth Post", "content": "This is the fourth post"},
    5: {"title": "Fifth Post", "content": "This is the fifth post"},
    6: {"title": "Sixth Post", "content": "This is the sixth post"},
    7: {"title": "Seventh Post", "content": "This is the seventh post"},
    8: {"title": "Eighth Post", "content": "This is the eighth post"},
    9: {"title": "Ninth Post", "content": "This is the ninth post"},
    10: {"title": "Tenth Post", "content": "This is the tenth post"},
}

@app.get("/posts")
def get_all_posts(limit: int = None):
    if limit:
        # answer = ''
        # for key in list(text_posts.keys())[:limit]:
        #     answer += f"{key}: {text_posts[key]['title']} content: {text_posts[key]['content']} "
        # return answer
    
        return {key: text_posts[key] for key in list(text_posts.keys())[:limit]}
    return text_posts

@app.get("/posts/{post_id}")
def get_ind_post(post_id: int):
    if post_id in text_posts:
        return text_posts[post_id]
    else:
        return HTTPException(status_code=404, detail="Not found")


@app.post("/posts")
def create_post(post: Post):

    new_post = {
        "title": post.title, 
        "content": post.content
        }
    
    text_posts[max(text_posts.keys()) + 1] = new_post
    
    # for i in range(100000):
    #     text_posts[max(text_posts.keys()) + 1] = new_post

    return new_post
    