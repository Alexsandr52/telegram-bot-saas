"""
Bot Configuration
Loads bot settings, services, schedule, and custom commands from database
"""
import os
import asyncio
import json
from typing import Optional, List, Dict, Any
from datetime import time
from pydantic import BaseModel, Field
from loguru import logger


class ServiceInfo(BaseModel):
    """Service information"""
    id: str
    name: str
    description: Optional[str] = None
    price: float
    duration_minutes: int
    photo_url: Optional[str] = None


class ScheduleDay(BaseModel):
    """Schedule for a day"""
    day_of_week: int  # 0 = Monday
    start_time: str
    end_time: str
    is_working_day: bool
    break_start_time: Optional[str] = None
    break_end_time: Optional[str] = None


class CustomCommand(BaseModel):
    """Custom command configuration"""
    command: str  # e.g., "catalog" or "c"
    description: str
    handler_type: str  # 'catalog', 'about', 'custom'
    enabled: bool = True


class BotConfig(BaseModel):
    """Complete bot configuration loaded from database"""
    # Bot info
    bot_id: str
    bot_token: str
    bot_username: str
    bot_name: str

    # Business info
    business_name: Optional[str] = None
    business_description: Optional[str] = None
    business_address: Optional[str] = None
    business_phone: Optional[str] = None

    # Settings
    timezone: str = "Europe/Moscow"
    language: str = "ru"

    # Services (loaded from DB)
    services: List[ServiceInfo] = Field(default_factory=list)

    # Schedule (loaded from DB)
    schedule: List[ScheduleDay] = Field(default_factory=list)

    # Custom commands (loaded from DB)
    custom_commands: List[CustomCommand] = Field(default_factory=list)

    # Additional settings (JSONB)
    settings: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class ConfigManager:
    """
    Manages bot configuration loaded from database
    """

    def __init__(self, bot_id: str, database_url: str):
        """
        Initialize config manager

        Args:
            bot_id: Bot UUID
            database_url: Database connection string
        """
        self.bot_id = bot_id
        self.database_url = database_url
        self._config: Optional[BotConfig] = None
        self._db = None

    async def load_config(self) -> BotConfig:
        """
        Load complete bot configuration from database

        Returns:
            BotConfig with all settings
        """
        import asyncpg

        if self._db is None:
            self._db = await asyncpg.connect(self.database_url)

        # Load bot info
        bot_data = await self._db.fetchrow(
            """
            SELECT id, bot_token, bot_username, bot_name, business_name,
                   business_description, business_address, business_phone,
                   timezone, language, settings
            FROM bots
            WHERE id = $1
            """,
            self.bot_id
        )

        if not bot_data:
            raise ValueError(f"Bot {self.bot_id} not found in database")

        # Load services
        services_data = await self._db.fetch(
            """
            SELECT id, name, description, price, duration_minutes, photo_url
            FROM services
            WHERE bot_id = $1 AND is_active = true
            ORDER BY sort_order
            """,
            self.bot_id
        )

        services = [
            ServiceInfo(
                id=str(row['id']),
                name=row['name'],
                description=row['description'],
                price=float(row['price']),
                duration_minutes=row['duration_minutes'],
                photo_url=row['photo_url']
            )
            for row in services_data
        ]

        # Load schedule
        schedule_data = await self._db.fetch(
            """
            SELECT day_of_week, start_time, end_time, is_working_day,
                   break_start_time, break_end_time
            FROM schedules
            WHERE bot_id = $1
            ORDER BY day_of_week
            """,
            self.bot_id
        )

        schedule = [
            ScheduleDay(
                day_of_week=row['day_of_week'],
                start_time=row['start_time'].strftime('%H:%M'),
                end_time=row['end_time'].strftime('%H:%M'),
                is_working_day=row['is_working_day'],
                break_start_time=row['break_start_time'].strftime('%H:%M') if row['break_start_time'] else None,
                break_end_time=row['break_end_time'].strftime('%H:%M') if row['break_end_time'] else None
            )
            for row in schedule_data
        ]

        # Parse settings JSON
        settings_dict = {}
        if bot_data['settings']:
            if isinstance(bot_data['settings'], str):
                settings_dict = json.loads(bot_data['settings'])
            else:
                settings_dict = bot_data['settings']

        # Extract custom commands from settings
        custom_commands = []
        if 'custom_commands' in settings_dict:
            custom_commands = [
                CustomCommand(**cmd)
                for cmd in settings_dict.get('custom_commands', [])
                if cmd.get('enabled', True)
            ]

        # Create config
        self._config = BotConfig(
            bot_id=str(bot_data['id']),
            bot_token=bot_data['bot_token'],
            bot_username=bot_data['bot_username'],
            bot_name=bot_data['bot_name'] or bot_data['bot_username'],
            business_name=bot_data['business_name'],
            business_description=bot_data['business_description'],
            business_address=bot_data['business_address'],
            business_phone=bot_data['business_phone'],
            timezone=bot_data['timezone'] or 'Europe/Moscow',
            language=bot_data['language'] or 'ru',
            services=services,
            schedule=schedule,
            custom_commands=custom_commands,
            settings=settings_dict
        )

        logger.info(f"Config loaded for bot {self.bot_id}: {len(services)} services, {len(schedule)} schedule days")

        return self._config

    async def reload_config(self) -> BotConfig:
        """Reload configuration from database"""
        return await self.load_config()

    @property
    def config(self) -> BotConfig:
        """Get current config (must be loaded first)"""
        if self._config is None:
            raise RuntimeError("Config not loaded. Call load_config() first.")
        return self._config

    async def close(self) -> None:
        """Close database connection"""
        if self._db:
            await self._db.close()
            self._db = None


# Global config instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> Optional[ConfigManager]:
    """Get global config manager"""
    return _config_manager


def set_config_manager(manager: ConfigManager) -> None:
    """Set global config manager"""
    global _config_manager
    _config_manager = manager
