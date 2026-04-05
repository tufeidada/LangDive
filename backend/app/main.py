import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import content, vocab, settings as settings_router, events

app = FastAPI(title="LangDive API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static audio files
os.makedirs(settings.AUDIO_DIR, exist_ok=True)
app.mount("/static/audio", StaticFiles(directory=settings.AUDIO_DIR), name="audio")

# Routers
app.include_router(content.router, prefix="/api")
app.include_router(vocab.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")
app.include_router(events.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
