"""
Configuration management for Web API
Loads settings from environment variables
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


def get_project_root() -> Path:
    """Get project root directory"""
    return Path(__file__).parent.parent.parent.parent


class Settings(BaseSettings):
    """Application settings"""

    # ============================================
    # Application
    # ============================================
    APP_NAME: str = "WebAPI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    API_PREFIX: str = "/api/v1"

    # ============================================
    # Server
    # ============================================
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ============================================
    # Database
    # ============================================
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/bot_saas",
        description="PostgreSQL connection URL"
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ============================================
    # Security
    # ============================================
    JWT_SECRET_KEY: str = Field(..., description="JWT secret key for sessions")
    JWT_ALGORITHM: str = "HS256"
    SESSION_EXPIRATION_HOURS: int = 24

    # ============================================
    # CORS
    # ============================================
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="CORS allowed origins (comma-separated)"
    )

    def get_cors_origins(self) -> list[str]:
        """Parse CORS origins from comma-separated string"""
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(',')]
        return self.CORS_ORIGINS

    # ============================================
    # Paths
    # ============================================
    PROJECT_ROOT: Path = Field(default_factory=get_project_root)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        case_sensitive = True


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance (singleton)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
