"""
Bot Template - Main Entry Point
Master's bot for client bookings
"""
import asyncio
import sys
import os
from pathlib import Path
from loguru import logger
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.config import ConfigManager, set_config_manager
from utils.db import BotDatabase, set_database
from handlers import client_menu, services, booking, profile


# ============================================
# Configuration
# ============================================

# Get environment variables
BOT_ID = os.getenv("BOT_ID")  # Bot UUID from database
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Bot token (decrypted)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@database:5432/bot_saas")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

if not BOT_ID:
    raise ValueError("BOT_ID environment variable is required")


# Configure logger
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
    level="INFO"
)


# ============================================
# Bot Setup
# ============================================

async def setup_bot() -> tuple[Bot, Dispatcher]:
    """
    Initialize bot and dispatcher

    Returns:
        Tuple of (Bot, Dispatcher)
    """
    # Load bot configuration from database
    config_manager = ConfigManager(BOT_ID, DATABASE_URL)
    await config_manager.load_config()
    set_config_manager(config_manager)

    config = config_manager.config
    logger.info(f"Bot config loaded: {config.bot_name}")

    # Initialize database
    db = BotDatabase(DATABASE_URL, BOT_ID)
    await db.connect()
    set_database(db)

    # Create bot
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.MARKDOWN,
            link_preview_is_disabled=False
        )
    )

    # Create dispatcher
    dp = Dispatcher(storage=MemoryStorage())

    # Register handlers
    dp.include_router(client_menu.router)
    dp.include_router(services.router)
    dp.include_router(booking.router)
    dp.include_router(profile.router)

    logger.info(f"Bot handlers registered")

    return bot, dp


async def config_reloader():
    """Periodically reload bot configuration to pick up changes"""
    from utils.config import get_config_manager as get_cfg
    import asyncio

    while True:
        try:
            await asyncio.sleep(60)  # Reload every 60 seconds
            config_manager = get_cfg()
            if config_manager:
                await config_manager.reload_config()
                logger.debug("Config reloaded")
        except Exception as e:
            logger.error(f"Error reloading config: {e}")


async def main() -> None:
    """Main function to run the bot"""

    # Setup bot
    bot, dp = await setup_bot()

    # Get bot info
    try:
        bot_info = await bot.get_me()
        logger.info(f"Bot started: @{bot_info.username} (ID: {bot_info.id})")
    except Exception as e:
        logger.error(f"Failed to get bot info: {e}")
        return

    # Start config reloader task
    import asyncio
    reloader_task = asyncio.create_task(config_reloader())

    # Start polling
    logger.info("Starting polling mode...")
    try:
        await dp.start_polling(bot)
    finally:
        # Cleanup
        reloader_task.cancel()
        config_manager = get_config_manager()
        db = get_database()

        if config_manager:
            await config_manager.close()
        if db:
            await db.close()


# ============================================
# Helper Functions
# ============================================

def get_config_manager():
    """Get global config manager"""
    from utils.config import get_config_manager as get_cfg
    return get_cfg()


def get_database():
    """Get global database"""
    from utils.db import get_database as get_db
    return get_db()


# ============================================
# Entry Point
# ============================================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
