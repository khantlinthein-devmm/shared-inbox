import mimetypes
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_v1
from app.api.v1.ws import router as ws_router
from app.core.config import get_settings
from app.core.database import engine

settings = get_settings()

# Slim Python images ship without /etc/mime.types; without these, /uploads would
# serve voice notes and stickers as text/plain and browsers refuse to play them.
for _type, _ext in (
    ("audio/ogg", ".ogg"),
    ("audio/ogg", ".oga"),
    ("audio/mp4", ".m4a"),
    ("audio/webm", ".weba"),
    ("image/webp", ".webp"),
):
    mimetypes.add_type(_type, _ext)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tables are created by `python init_db.py`; Alembic recommended for prod.
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1)
app.include_router(ws_router)

Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")


@app.get("/")
async def root() -> dict:
    return {"name": settings.app_name, "docs": "/docs", "ws": "/api/v1/ws"}