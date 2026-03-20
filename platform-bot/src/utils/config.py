"""
Configuration management for Platform Bot
Loads settings from environment variables
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


def get_project_root() -> Path:
    """Get project root directory"""
    return Path(__file__).parent.parent.parent.parent


class Settings(BaseSettings):
    """Application settings"""

    # ============================================
    # Application
    # ============================================
    APP_NAME: str = "PlatformBot"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ============================================
    # Telegram Bot
    # ============================================
    BOT_TOKEN: str = Field(..., description="Telegram bot token from @BotFather")
    BOT_WEBHOOK_SECRET: Optional[str] = Field(None, description="Webhook secret token")
    BOT_WEBHOOK_MODE: bool = Field(False, description="Use webhook instead of polling")
    BOT_WEBHOOK_PATH: str = "/webhook/platform-bot"
    BOT_WEBHOOK_URL: Optional[str] = Field(None, description="Full webhook URL")

    # ============================================
    # Database
    # ============================================
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/bot_saas",
        description="PostgreSQL connection URL (async)"
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ============================================
    # Redis
    # ============================================
    REDIS_URL: str = Field(
        default="redis://:redis123@localhost:6379/0",
        description="Redis connection URL"
    )
    REDIS_ENABLED: bool = True

    # ============================================
    # Security
    # ============================================
    ENCRYPTION_KEY: bytes = Field(
        default=b'',
        description="Fernet key for token encryption (generate with cryptography)"
    )
    JWT_SECRET_KEY: str = Field(..., description="JWT secret key for sessions")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # ============================================
    # Factory Service
    # ============================================
    FACTORY_SERVICE_URL: str = Field(
        default="http://factory-service:8001",
        description="Factory Service API URL"
    )
    FACTORY_SERVICE_TIMEOUT: int = 30  # seconds

    # ============================================
    # Web Panel
    # ============================================
    WEB_PANEL_URL: str = Field(
        default="http://localhost:3000",
        description="Web panel URL for masters"
    )

    # ============================================
    # Docker
    # ============================================
    DOCKER_HOST: Optional[str] = Field(
        default="unix:///var/run/docker.sock",
        description="Docker daemon socket"
    )
    BOT_CONTAINER_NETWORK: str = "bot_saas_network"
    BOT_TEMPLATE_IMAGE: str = "telegram-bot-saas/bot-template:latest"

    # ============================================
    # Paths
    # ============================================
    PROJECT_ROOT: Path = Field(default_factory=get_project_root)
    LOG_FILE_PATH: Optional[str] = None

    # ============================================
    # Features
    # ============================================
    ENABLE_ANALYTICS: bool = True
    ENABLE_RATE_LIMITING: bool = True
    RATE_LIMIT_PER_MINUTE: int = 30

    @field_validator('ENCRYPTION_KEY', mode='before')
    @classmethod
    def parse_encryption_key(cls, v: str) -> bytes:
        """Parse encryption key from string to bytes"""
        if isinstance(v, str):
            return v.encode() if v else os.urandom(44)
        return v

    @field_validator('DATABASE_URL')
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format"""
        if not v.startswith(('postgresql://', 'postgresql+asyncpg://')):
            raise ValueError('DATABASE_URL must start with postgresql:// or postgresql+asyncpg://')
        return v

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


def reload_settings() -> Settings:
    """Reload settings from environment"""
    global _settings
    _settings = Settings()
    return _settings
