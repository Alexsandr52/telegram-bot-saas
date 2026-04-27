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
from src.utils.analytics import log_platform_event, PlatformEventType
from src.keyboards import get_main_menu_keyboard, get_subscription_keyboard, create_back_button


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

        # Log analytics event
        await log_platform_event(
            PlatformEventType.BOT_STARTED,
            master_id=master['id'],
            user_id=telegram_id
        )

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
    bot_repo = get_bot_repo()

    try:
        master = await master_repo.get_master_by_telegram_id(telegram_id)
        if not master:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Get master's bots
        bots = await bot_repo.get_master_bots(master['id'])

        # Initialize counters
        total_appointments = 0
        total_clients = set()
        total_revenue = 0
        active_bots = 0

        # Collect statistics from all bots
        from src.utils.db import AppointmentRepository
        for bot in bots:
            if bot.get('is_active'):
                active_bots += 1

            appt_repo = AppointmentRepository(bot_repo.db)
            appointments = await appt_repo.get_bot_appointments(bot['id'], limit=1000)

            for appt in appointments:
                total_appointments += 1
                client_id = appt.get('client_id')
                if client_id:
                    total_clients.add(client_id)

                # Count revenue from completed appointments
                if appt.get('status') == 'completed':
                    total_revenue += appt.get('price', 0)

        # SUBSCRIPTION DISABLED: No subscription display
        stats_text = (
            f"📊 *Ваша статистика*\n\n"
            f"🤖 Ботов: {len(bots)} (активных: {active_bots})\n"
            f"👥 Уникальных клиентов: {len(total_clients)}\n"
            f"📋 Всего записей: {total_appointments}\n"
            f"💰 Заработано: {total_revenue:.0f} ₽"
        )

        await callback.message.edit_text(
            stats_text,
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()

        # Log analytics event
        await log_platform_event(
            PlatformEventType.STATISTICS_VIEWED,
            master_id=master['id'],
            user_id=telegram_id
        )

    except Exception as e:
        logger.error(f"Error showing statistics: {e}")
        await callback.answer("❌ Ошибка при загрузке статистики", show_alert=True)


@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery) -> None:
    """Show settings menu"""
    telegram_id = callback.from_user.id
    master_repo = get_master_repo()

    try:
        master = await master_repo.get_master_by_telegram_id(telegram_id)
        if not master:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # SUBSCRIPTION DISABLED: No subscription display in settings
        settings_text = (
            f"⚙️ *Настройки*\n\n"
            f"👤 *Профиль*\n"
            f"Имя: {master.get('full_name') or 'Не указано'}\n"
            f"Username: @{master.get('username', 'Не указано')}\n"
            f"Телефон: {master.get('phone', 'Не указан')}\n\n"
            f"_Изменить профиль можно через меню управления._"
        )

        from ..keyboards import get_settings_keyboard

        await callback.message.edit_text(
            settings_text,
            parse_mode="Markdown",
            reply_markup=get_settings_keyboard()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error showing settings: {e}")
        await callback.answer("❌ Ошибка при загрузке настроек", show_alert=True)


# ============================================
# Web Panel Handler
# ============================================

@router.callback_query(F.data == "web_panel")
async def web_panel_button(callback: CallbackQuery) -> None:
    """Web panel button handler"""
    telegram_id = callback.from_user.id
    master_repo = get_master_repo()

    try:
        master = await master_repo.get_master_by_telegram_id(telegram_id)
        if not master:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Generate auth token for web panel
        from src.utils.db import SessionRepository
        from datetime import timedelta
        import secrets
        import os

        session_repo = SessionRepository(master_repo.db)
        session_token = secrets.token_urlsafe(32)

        # Create session (24 hours expiry)
        await master_repo.db.execute(
            """
            INSERT INTO user_sessions (master_id, session_token, expires_at)
            VALUES ($1, $2, NOW() + INTERVAL '24 hours')
            """,
            master['id'],
            session_token
        )

        # Get web panel URL from settings
        from src.utils.config import get_settings
        settings = get_settings()

        web_url = settings.WEB_PANEL_URL or "http://localhost:3000"
        auth_url = f"{web_url}/auth?token={session_token}"

        await callback.message.edit_text(
            "🌐 *Веб-панель*\n\n"
            "Нажмите кнопку ниже для входа в веб-панель:\n\n"
            f"_Ссылка действительна 24 часа_",
            parse_mode="Markdown",
            reply_markup=create_back_button("main_menu")
        )

        # Send separate message with URL button
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Открыть веб-панель", url=auth_url)]
        ])

        await callback.message.answer(
            "🔗 Ссылка для входа:",
            reply_markup=keyboard
        )

        # Log analytics event
        await log_platform_event(
            PlatformEventType.WEB_PANEL_OPENED,
            master_id=master['id'],
            user_id=telegram_id
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in web panel handler: {e}")
        await callback.answer("❌ Ошибка при получении ссылки", show_alert=True)


# ============================================
# Subscription Handler (DISABLED)
# ============================================

# SUBSCRIPTION DISABLED: This handler is disabled
# Uncomment and implement when subscription system is ready
#
# @router.callback_query(F.data == "subscription")
# async def subscription_button(callback: CallbackQuery) -> None:
#     """Subscription button handler"""
#     telegram_id = callback.from_user.id
#     master_repo = get_master_repo()
#     sub_repo = get_subscription_repo()
#
#     try:
#         master = await master_repo.get_master_by_telegram_id(telegram_id)
#         if not master:
#             await callback.answer("❌ Пользователь не найден", show_alert=True)
#             return
#
#         # Get subscription info
#         subscription = await sub_repo.get_active_subscription(master['id'])
#
#         if subscription:
#             plan_name = subscription.get('plan_name', 'Free')
#             expires_at = subscription.get('expires_at')
#             bots_limit = subscription.get('bots_limit', 1)
#
#             if expires_at:
#                 expiry_str = expires_at.strftime('%d.%m.%Y')
#                 expiry_text = f"до {expiry_str}"
#             else:
#                 expiry_text = "бессрочно"
#
#             text = (
#                 f"💳 *Ваша подписка*\n\n"
#                 f"📦 Тариф: {plan_name}\n"
#                 f"🤖 Лимит ботов: {bots_limit}\n"
#                 f"📅 Действует: {expiry_text}\n\n"
#                 f"Хотите изменить тариф?"
#             )
#         else:
#             text = (
#                 "💳 *Ваша подписка*\n\n"
#                 "🆓 Текущий тариф: Free\n"
#                 "🤖 Лимит ботов: 1\n\n"
#                 "Улучшите тариф для доступа к дополнительным функциям:"
#             )
#
#         await callback.message.edit_text(
#             text,
#             parse_mode="Markdown",
#             reply_markup=get_subscription_keyboard(
#                 current_plan=subscription.get('plan_name', 'free').lower() if subscription else 'free'
#             )
#         )
#
#         # Log analytics event
#         await log_platform_event(
#             PlatformEventType.SUBSCRIPTION_VIEWED,
#             master_id=master['id'],
#             user_id=telegram_id
#         )
#
#         await callback.answer()
#
#     except Exception as e:
#         logger.error(f"Error in subscription handler: {e}")
#         await callback.answer("❌ Ошибка при загрузке подписки", show_alert=True)
