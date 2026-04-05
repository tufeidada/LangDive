import os
from app.config import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("YOUTUBE_API_KEY", "AIza-test")
    monkeypatch.setenv("AUDIO_DIR", "./data/audio")
    settings = Settings()
    assert settings.DATABASE_URL == "postgresql+asyncpg://test:test@localhost/test"
    assert settings.OPENROUTER_API_KEY == "sk-test"
    assert settings.AUDIO_DIR == "./data/audio"
