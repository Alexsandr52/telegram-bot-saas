"""
Platform Bot - Main Entry Point
Simplified version for testing
"""
import asyncio
import sys
from pathlib import Path
from loguru import logger
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================
# Configuration
# ============================================

from src.utils.config import get_settings
settings = get_settings()

# Configure logger
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)


# ============================================
# Handlers
# ============================================

async def cmd_start(message: Message) -> None:
    """Simple /start handler"""
    await message.answer(
        "👋 *Добро пожаловать в Bot SaaS Platform!*\n\n"
        "Бот работает! 🎉\n\n"
        "Функционал в разработке...",
        parse_mode="Markdown"
    )
    logger.info(f"User {message.from_user.id} sent /start")


async def cmd_help(message: Message) -> None:
    """Help command"""
    await message.answer(
        "📚 *Справка*\n\n"
        "/start - Главное меню\n"
        "/help - Эта справка",
        parse_mode="Markdown"
    )


# ============================================
# Main
# ============================================

async def main() -> None:
    """Main function to run the bot"""

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

    # Register handlers
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_help, Command("help"))

    # Get bot info
    try:
        bot_info = await bot.get_me()
        logger.info(f"Bot started: @{bot_info.username} (ID: {bot_info.id})")
    except Exception as e:
        logger.error(f"Failed to get bot info: {e}")
        return

    # Start polling
    logger.info("Starting polling mode...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
