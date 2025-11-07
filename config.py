# config.py
from pydantic import BaseSettings
from typing import List, Optional
from pathlib import Path
import os

class Settings(BaseSettings):
    UPLOAD_DIR: str = "uploads"
    CORS_ORIGINS: Optional[str] = "*"
    MODEL_USE_GPU: bool = False
    
    # PostgreSQL Configuration
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "password"
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: str = "5432"
    DATABASE_NAME: str = "kcr_db"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @property
    def UPLOAD_PATH(self) -> Path:
        path = Path(self.UPLOAD_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct PostgreSQL connection URL from individual components"""
        return f"postgresql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
    
    def get_cors_origins(self) -> List[str]:
        if not self.CORS_ORIGINS:
            return []
        return [u.strip() for u in str(self.CORS_ORIGINS).split(",") if u.strip()]

settings = Settings()
