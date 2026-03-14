"""
Notification Service - Configuration
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application settings"""

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@database:5432/bot_saas")

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://:redis123@redis:6379/0")
    REDIS_ENABLED: bool = os.getenv("REDIS_ENABLED", "true").lower() == "true"

    # Notification settings
    NOTIFICATION_CHECK_INTERVAL: int = int(os.getenv("NOTIFICATION_CHECK_INTERVAL", "300"))  # 5 minutes
    NOTIFICATION_WORKER_CONCURRENCY: int = int(os.getenv("NOTIFICATION_WORKER_CONCURRENCY", "2"))

    # Retry settings
    MAX_RETRY_ATTEMPTS: int = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
    RETRY_DELAY_SECONDS: int = int(os.getenv("RETRY_DELAY_SECONDS", "300"))  # 5 minutes

    # Telegram API
    TELEGRAM_API_URL: str = "https://api.telegram.org/bot{token}/{method}"

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")

    # Environment
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    TEST_MODE: bool = os.getenv("TEST_MODE", "false").lower() == "true"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings instance"""
    return settings