from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://langdive:langdive_dev@localhost:5432/langdive"
    OPENROUTER_API_KEY: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    DASHSCOPE_API_KEY: str = ""
    YOUTUBE_API_KEY: str = ""
    AUDIO_DIR: str = "./data/audio"
    DAILY_PIPELINE_HOUR: int = 6

    class Config:
        env_file = ".env"


settings = Settings()
