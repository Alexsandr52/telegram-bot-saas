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


# Add src and parent directory to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(project_root))

from src.utils.config import get_settings
from src.utils.db import Database
from src.utils.repositories import init_repositories
# Import error logging if available
try:
    from shared.error_logging import init_error_logging, close_error_logging, log_exception, ErrorLevel, ErrorCategory
except ImportError:
    logger.warning("Shared error logging module not found, continuing without it")
    # Define stubs for error logging functions
    def init_error_logging(*args, **kwargs):
        pass
    def close_error_logging(*args, **kwargs):
        pass
    def log_exception(*args, **kwargs):
        pass
    class ErrorLevel:
        DEBUG = "DEBUG"
        INFO = "INFO"
        ERROR = "ERROR"
    class ErrorCategory:
        DATABASE = "DATABASE"
        API = "API"
        BOT = "BOT"

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
    """Initialize database connection and error logging"""
    db = Database(settings.DATABASE_URL)
    await db.connect()
    init_repositories(db)

    # Initialize error logging system
    try:
        await init_error_logging()
    except Exception as e:
        logger.warning(f"Failed to initialize error logging: {e}")

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

    # Add error handler for unhandled exceptions
    from aiogram import types
    from aiogram.exceptions import TelegramBadRequest

    @dp.errors()
    async def error_handler(event, exception):
        """Global error handler for all exceptions"""
        logger.error(f"Unhandled exception: {exception}", exc_info=True)

        # Get user_id and context
        user_id = event.from_user.id if hasattr(event, 'from_user') and event.from_user else None
        context = {
            'event_type': type(event).__name__,
            'user_id': str(user_id) if user_id else None
        }

        # Log to error_logs database
        try:
            # Determine error category
            error_category = ErrorCategory.SYSTEM
            if 'telegram' in type(exception).__name__.lower() or 'aiogram' in type(exception).__module__:
                error_category = ErrorCategory.TELEGRAM_API
            elif 'postgres' in str(exception).lower() or 'database' in str(exception).lower():
                error_category = ErrorCategory.DATABASE

            # Determine error level
            error_level = ErrorLevel.ERROR
            if isinstance(exception, TelegramBadRequest):
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
                service_name='platform-bot'
            )

            # Also log to analytics for tracking
            from src.utils.analytics import log_platform_event, PlatformEventType
            await log_platform_event(
                PlatformEventType.BOT_ERROR,
                user_id=user_id,
                event_data={
                    'error_type': type(exception).__name__,
                    'error_message': str(exception),
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
            await event.answer("😔 Произошла ошибка. Попробуйте снова.", show_alert=True)

    # Get bot info
    try:
        bot_info = await bot.get_me()
        logger.info(f"Platform Bot started: @{bot_info.username} (ID: {bot_info.id})")
    except Exception as e:
        logger.error(f"Failed to get bot info: {e}")
        return

    # Check webhook mode
    if settings.BOT_WEBHOOK_MODE:
        # Webhook mode
        webhook_url = settings.BOT_WEBHOOK_URL or f"{settings.WEB_PANEL_URL}{settings.BOT_WEBHOOK_PATH}"
        logger.info(f"Starting webhook mode on {webhook_url}...")

        # Set webhook
        await bot.set_webhook(
            url=webhook_url,
            secret_token=settings.BOT_WEBHOOK_SECRET
        )

        # Create aiohttp application
        app = web.Application()

        # Create webhook handler
        webhook_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
            secret_token=settings.BOT_WEBHOOK_SECRET
        )

        # Setup application
        webhook_requests_handler = webhook_handler.handle
        setup_application(app, dp, bot=bot)

        # Add webhook route
        app.router.add_post(settings.BOT_WEBHOOK_PATH, webhook_requests_handler)

        # Start aiohttp server
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=8080)
        await site.start()
        logger.info(f"Webhook server started on 0.0.0.0:8080")

        try:
            # Keep the server running
            while True:
                await asyncio.sleep(3600)
        finally:
            # Cleanup
            await bot.delete_webhook()
            await runner.cleanup()
            from src.utils.repositories import get_db
            db = get_db()
            if db:
                await db.close()
            await close_error_logging()
    else:
        # Polling mode
        logger.info("Starting polling mode...")
        try:
            await dp.start_polling(bot)
        finally:
            # Cleanup
            from src.utils.repositories import get_db
            db = get_db()
            if db:
                await db.close()
            await close_error_logging()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
