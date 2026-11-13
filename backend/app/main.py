from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.exceptions import AppError, app_error_handler
from app.logging_config import configure_logging
from app.routers import auth, health, history, me, quiz, report, sessions

configure_logging()

app = FastAPI(title="衰衰闯关 API", version="0.2.0")

app.add_exception_handler(AppError, app_error_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings = get_settings()
upload_root = Path(settings.upload_dir)
upload_root.mkdir(parents=True, exist_ok=True)
(upload_root / "avatars").mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_root)), name="uploads")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(me.router)
app.include_router(quiz.router)
app.include_router(report.router)
app.include_router(sessions.router)
app.include_router(history.router)
