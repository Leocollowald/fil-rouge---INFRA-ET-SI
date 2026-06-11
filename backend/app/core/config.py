from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    APP_NAME: str = "Y-Plaza"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_URL: str

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Stockage images
    UPLOAD_DIR: Path = Path(__file__).resolve().parents[3] / "uploads"
    MAX_IMAGE_SIZE: int = 5 * 1024 * 1024  # 5 Mo
    ALLOWED_IMAGE_TYPES: list[str] = ["image/jpeg", "image/png", "image/webp"]

    class Config:
        env_file = str(ENV_FILE)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
