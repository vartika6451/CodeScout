from fastapi import FastAPI
from app.routes.health import router as health_router
from app.routes.analyze import router as analyze_router

app = FastAPI(title="CodeScout API")

app.include_router(health_router)
app.include_router(analyze_router)