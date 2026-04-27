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
from aiogram.types import Message
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.config import ConfigManager, set_config_manager
from utils.db import BotDatabase, set_database
from handlers import client_menu, services, booking, profile

# Add shared module path for error logging
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'shared'))
from error_logging import init_error_logging, close_error_logging, log_exception, ErrorLevel, ErrorCategory

# ============================================
# Configuration
# ============================================

# Get environment variables
BOT_ID = os.getenv("BOT_ID")  # Bot UUID from database
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Bot token (decrypted)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@database:5432/bot_saas")
USE_WEBHOOK = os.getenv("USE_WEBHOOK", "0") == "1"
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", f"/webhook/{BOT_ID}")
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN", None)
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8080"))
TELEGRAM_PROXY = os.getenv("TELEGRAM_PROXY")  # Proxy for Telegram API

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

    # Initialize error logging system
    await init_error_logging(DATABASE_URL)

    # Create bot
    bot_config = {
        "token": BOT_TOKEN,
        "default": DefaultBotProperties(
            parse_mode=ParseMode.MARKDOWN,
            link_preview_is_disabled=False
        )
    }

    # Add proxy if configured (critical for Telegram API access in Russia)
    if TELEGRAM_PROXY:
        logger.info(f"Using proxy: {TELEGRAM_PROXY[:20]}...")
        bot_config["proxy"] = TELEGRAM_PROXY

    bot = Bot(**bot_config)

    # Create dispatcher
    dp = Dispatcher(storage=MemoryStorage())

    # Register handlers
    dp.include_router(client_menu.router)
    dp.include_router(services.router)
    dp.include_router(booking.router)
    dp.include_router(profile.router)

    # Add global error handler
    from aiogram import types
    from aiogram.exceptions import TelegramBadRequest, TelegramForbidden, TelegramNotFound

    @dp.errors()
    async def error_handler(event, exception):
        """Global error handler for all exceptions"""
        logger.error(f"Unhandled exception: {exception}", exc_info=True)

        # Get user_id and context
        user_id = event.from_user.id if hasattr(event, 'from_user') and event.from_user else None
        context = {
            'event_type': type(event).__name__,
            'user_id': str(user_id) if user_id else None,
            'bot_id': BOT_ID
        }

        # Log to error_logs database
        try:
            # Determine error category
            error_category = ErrorCategory.BUSINESS_LOGIC
            if 'telegram' in type(exception).__name__.lower() or 'aiogram' in type(exception).__module__:
                error_category = ErrorCategory.TELEGRAM_API
            elif 'postgres' in str(exception).lower() or 'database' in str(exception).lower():
                error_category = ErrorCategory.DATABASE

            # Determine error level
            error_level = ErrorLevel.ERROR
            if isinstance(exception, (TelegramBadRequest, TelegramForbidden)):
                # Expected user errors - WARNING level
                error_level = ErrorLevel.WARNING
            elif "CRITICAL" in str(exception).upper() or "FATAL" in str(exception).upper():
                # Critical errors
                error_level = ErrorLevel.CRITICAL

            # Log to database
            await log_exception(
                exception=exception,
                level=error_level,
                category=error_category,
                context=context,
                user_id=user_id,
                bot_id=BOT_ID,
                service_name='bot-template'
            )

            # Also log to analytics for tracking
            if hasattr(db, 'log_analytics_event'):
                await db.log_analytics_event(
                    'bot_error',
                    user_id=user_id,
                    event_data={
                        'exception': type(exception).__name__,
                        'message': str(exception),
                        'event_type': type(event).__name__,
                        'error_level': error_level.value,
                        'error_category': error_category.value
                    }
                )
        except Exception as log_error:
            logger.error(f"Failed to log error: {log_error}")

        # Send error response to user
        if isinstance(event, types.Message):
            await event.answer("😔 Произошла ошибка. Пожалуйста, попробуйте позже.")
        elif isinstance(event, types.CallbackQuery):
            try:
                await event.answer("😔 Произошла ошибка. Попробуйте снова.", show_alert=True)
            except Exception:
                pass

    logger.info("Bot handlers registered")

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
    reloader_task = asyncio.create_task(config_reloader())

    # Start polling or webhook
    if USE_WEBHOOK:
        logger.info(f"Starting webhook mode on {WEBHOOK_HOST}:{WEBHOOK_PORT}{WEBHOOK_PATH}...")
        try:
            await dp.start_webhook(
                bot=bot,
                webhook_path=WEBHOOK_PATH,
                host=WEBHOOK_HOST,
                port=WEBHOOK_PORT,
                secret_token=WEBHOOK_SECRET_TOKEN
            )
        finally:
            # Cleanup
            reloader_task.cancel()
            config_manager = get_config_manager()
            db = get_database()

            if config_manager:
                await config_manager.close()
            if db:
                await db.close()
            await close_error_logging()
    else:
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
            await close_error_logging()


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
