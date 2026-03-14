"""
Platform Bot - Main Entry Point
Bot for masters to manage their booking bots
"""
import asyncio
import sys
from pathlib import Path
from loguru import logger
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import get_settings
from src.utils.db import Database
from src.utils.repositories import init_repositories

# Import routers
from src.handlers import start, connect_bot, services, appointments, schedule, auth


# ============================================
# Configuration
# ============================================

settings = get_settings()

# Configure logger
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)


# ============================================
# Database
# ============================================

async def init_db():
    """Initialize database connection"""
    db = Database(settings.DATABASE_URL)
    await db.connect()
    init_repositories(db)
    logger.info("Database initialized")


# ============================================
# Main
# ============================================

async def main() -> None:
    """Main function to run the bot"""

    # Initialize database
    await init_db()

    # Create bot
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.MARKDOWN,
            link_preview_is_disabled=False
        )
    )

    # Create dispatcher
    dp = Dispatcher(storage=MemoryStorage())

    # Register routers
    dp.include_router(start.router)
    dp.include_router(connect_bot.router)
    dp.include_router(services.router)
    dp.include_router(appointments.router)
    dp.include_router(schedule.router)
    dp.include_router(auth.router)

    # Get bot info
    try:
        bot_info = await bot.get_me()
        logger.info(f"Platform Bot started: @{bot_info.username} (ID: {bot_info.id})")
    except Exception as e:
        logger.error(f"Failed to get bot info: {e}")
        return

    # Start polling
    logger.info("Starting polling mode...")
    try:
        await dp.start_polling(bot)
    finally:
        # Cleanup
        from src.utils.repositories import get_db
        db = get_db()
        if db:
            await db.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
