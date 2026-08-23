from fastapi import FastAPI

from app.routes import health
from app.routes import analyze
from app.routes import chat


app = FastAPI()


app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(chat.router)