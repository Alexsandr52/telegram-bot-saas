"""
Auth Handler for Platform Bot
Handles web panel authentication
"""
import secrets
import string
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from loguru import logger

from src.utils.repositories import get_master_repo, get_session_repo
from src.utils.config import get_settings


router = Router(name="auth_handler")


def generate_web_token(length: int = 8) -> str:
    """Generate a secure random token for web authentication"""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@router.callback_query(F.data == "web_panel")
async def web_panel_auth(callback: CallbackQuery) -> None:
    """
    Generate one-time token for web panel authentication
    """
    master_repo = get_master_repo()
    session_repo = get_session_repo()

    telegram_id = callback.from_user.id

    try:
        # Get master
        master = await master_repo.get_master_by_telegram_id(telegram_id)
        if not master:
            await callback.answer("❌ Пользователь не найден. Напишите /start", show_alert=True)
            return

        # Generate unique token
        token = generate_web_token()

        # Create session
        session_id = await session_repo.create_session(
            master_id=master['id'],
            session_token=token,
            ip_address=None,  # Will be set when user logs in from web
            user_agent=None,
            expires_hours=24
        )

        settings = get_settings()
        web_url = settings.WEB_PANEL_URL

        text = (
            "🌐 *Вход в веб-панель*\n\n"
            f"Ваш одноразовый код:\n\n"
            f"🔑 *{token}*\n\n"
            f"_Код действителен 24 часа_\n\n"
            "1. Откройте веб-панель\n"
            f"2. Введите код для входа\n\n"
            f"🔗 {web_url}"
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
            ]
        )

        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        await callback.answer()

        logger.info(f"Web token generated for user {telegram_id}: {token}")

    except Exception as e:
        logger.error(f"Error generating web token: {e}")
        await callback.answer("❌ Ошибка при генерации кода", show_alert=True)
