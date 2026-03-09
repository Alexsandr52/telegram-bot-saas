"""
/start command handler for Platform Bot
Handles user registration and main menu
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from loguru import logger

from src.utils.db import MasterRepository, BotRepository, SubscriptionRepository
from src.utils.repositories import get_master_repo, get_bot_repo, get_subscription_repo
from src.keyboards import get_main_menu_keyboard


router = Router(name="start_handler")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """
    Handle /start command
    Register or update master and show main menu
    """
    # Get repositories from singletons
    master_repo = get_master_repo()

    telegram_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    try:
        # Register or update master
        master_id = await master_repo.create_master(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name
        )

        # Get master info
        master = await master_repo.get_master_by_telegram_id(telegram_id)

        # Welcome message
        if master and master['created_at']:
            is_new = (master['created_at'].replace(tzinfo=None) ==
                     message.date)  # Approximate check
        else:
            is_new = False

        if is_new:
            welcome_text = (
                "👋 *Добро пожаловать в Bot SaaS Platform!*\n\n"
                "Я помогу вам создать и управлять вашим Telegram-ботом "
                "для записи клиентов.\n\n"
                "🤖 *Что вы можете делать:*\n"
                "• Создавать ботов для своей услуги\n"
                "• Управлять услугами и графиком\n"
                "• Просматривать записи клиентов\n"
                "• Анализировать статистику\n\n"
                "📝 *Начните работу:*\n"
                "Нажмите *➕ Добавить бота* для создания первого бота\n\n"
                "💡 *Подсказка:* Сначала создайте бота через @BotFather "
                "и пришлите мне токен."
            )
        else:
            welcome_text = (
                f"👋 *С возвращением, {full_name}!*\n\n"
                "Добро пожаловать в панель управления Bot SaaS Platform\n\n"
                "Выберите действие в меню ниже:"
            )

        await message.answer(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard()
        )

        logger.info(f"User {telegram_id} (@{username}) started bot")

    except Exception as e:
        logger.error(f"Error in /start for user {telegram_id}: {e}")
        await message.answer(
            "😔 Произошла ошибка. Пожалуйста, попробуйте позже."
        )


@router.callback_query(F.data == "main_menu")
@router.callback_query(F.data == "back_to_main")
async def show_main_menu(callback: CallbackQuery) -> None:
    """Show main menu from callback"""
    await callback.message.edit_text(
        "🏠 *Главное меню*\n\nВыберите действие:",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help command"""
    help_text = (
        "📚 *Справка по командам:*\n\n"
        "/start — Главное меню\n"
        "/help — Эта справка\n"
        "/mybots — Мои боты\n"
        "/addbot — Добавить нового бота\n\n"
        "💡 *Как создать бота:*\n"
        "1. Откройте @BotFather в Telegram\n"
        "2. Напишите /newbot и следуйте инструкциям\n"
        "3. Скопируйте токен бота\n"
        "4. Отправьте токен мне через кнопку *➕ Добавить бота*\n\n"
        "❓ *Нужна помощь?*\n"
        "Обращайтесь в поддержку: @support_username"
    )

    await message.answer(help_text, parse_mode="Markdown")


@router.callback_query(F.data == "statistics")
async def show_statistics(callback: CallbackQuery) -> None:
    """Show user statistics"""
    telegram_id = callback.from_user.id
    master_repo = get_master_repo()

    try:
        master = await master_repo.get_master_by_telegram_id(telegram_id)
        if not master:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # TODO: Implement actual statistics
        stats_text = (
            "📊 *Ваша статистика*\n\n"
            f"🤖 Ботов: 0\n"
            f"👥 Клиентов: 0\n"
            f"📋 Записей: 0\n"
            f"💳 Тариф: Free\n\n"
            "_Более детальная статистика будет доступна после создания первого бота._"
        )

        await callback.message.edit_text(
            stats_text,
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error showing statistics: {e}")
        await callback.answer("❌ Ошибка при загрузке статистики", show_alert=True)


@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery) -> None:
    """Show settings menu"""
    settings_text = (
        "⚙️ *Настройки*\n\n"
        "Здесь вы можете настроить профиль и уведомления.\n\n"
        "Функция в разработке 🔨"
    )

    from ..keyboards import get_settings_keyboard

    await callback.message.edit_text(
        settings_text,
        parse_mode="Markdown",
        reply_markup=get_settings_keyboard()
    )
    await callback.answer()
