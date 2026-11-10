from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import health, quiz, report

app = FastAPI(title="衰衰闯关 API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(quiz.router)
app.include_router(report.router)
