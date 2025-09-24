from pydantic import BaseSettings, AnyHttpUrl, validator
from typing import List, Optional
from pathlib import Path
import os

class Settings(BaseSettings):
    UPLOAD_DIR: str = "uploads"
    CORS_ORIGINS: Optional[str] = "*"
    MODEL_USE_GPU: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def UPLOAD_PATH(self) -> Path:
        return Path(self.UPLOAD_DIR)

    def get_cors_origins(self) -> List[str]:
        # allows comma-separated list in .env
        if not self.CORS_ORIGINS:
            return []
        return [u.strip() for u in str(self.CORS_ORIGINS).split(",") if u.strip()]

# single settings instance for app-wide import
settings = Settings()
