"""
Connect bot handler for Platform Bot
Handles bot token registration and container creation
"""
import re
import httpx
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from src.utils.db import MasterRepository, BotRepository, SubscriptionRepository
from src.utils.encryption import encrypt_token
from src.utils.config import get_settings
from src.keyboards import (
    get_main_menu_keyboard,
    get_bots_list_keyboard,
    get_bot_actions_keyboard,
    create_back_button
)


router = Router(name="connect_bot_handler")


# ============================================
# FSM States
# ============================================

class ConnectBotStates(StatesGroup):
    """States for bot connection flow"""
    waiting_for_token = State()
    waiting_for_bot_name = State()
    waiting_for_business_name = State()


# ============================================
# Constants
# ============================================

BOT_TOKEN_PATTERN = r'^\d+:[A-Za-z0-9_-]{35}$'
BOTFather_LINK = "https://t.me/BotFather"


# ============================================
# Add Bot Flow
# ============================================

@router.callback_query(F.data == "add_bot")
@router.callback_query(F.data == "my_bots")
async def show_my_bots(callback: CallbackQuery) -> None:
    """Show user's bots or prompt to add new bot"""
    from src.utils.repositories import get_master_repo, get_bot_repo

    master_repo = get_master_repo()
    bot_repo = get_bot_repo()

    telegram_id = callback.from_user.id

    try:
        # Get master
        master = await master_repo.get_master_by_telegram_id(telegram_id)
        if not master:
            await callback.answer("❌ Сначала запустите бота через /start", show_alert=True)
            return

        # Get bots
        bots = await bot_repo.get_master_bots(master['id'])

        if not bots:
            # No bots yet - show prompt to add
            text = (
                "🤖 *Ваши боты*\n\n"
                "У вас пока нет добавленных ботов.\n\n"
                "Давайте создадим первого! Для этого:\n"
                f"1. Перейдите в [{BOTFather_LINK}]({BOTFather_LINK})\n"
                "2. Создайте нового бота (/newbot)\n"
                "3. Скопируйте токен\n"
                "4. Отправьте его мне\n\n"
                "Нажмите *Добавить бота* чтобы начать."
            )

            keyboard = get_main_menu_keyboard()
            # Add button to start adding bot
            keyboard.inline_keyboard.insert(0, [
                InlineKeyboardButton(text="➕ Добавить бота", callback_data="start_add_bot")
            ])

        else:
            # Show list of bots
            text = "🤖 *Ваши боты*\n\nВыберите бота для управления:"
            keyboard = get_bots_list_keyboard(bots)

        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in show_my_bots: {e}")
        await callback.answer("❌ Ошибка при загрузке списка ботов", show_alert=True)


@router.callback_query(F.data == "start_add_bot")
async def start_add_bot(callback: CallbackQuery, state: FSMContext) -> None:
    """Start the add bot flow"""
    text = (
        f"➕ *Добавление бота*\n\n"
        f"Для создания бота вам понадобится токен от [@BotFather]({BOTFather_LINK})\n\n"
        f"📝 *Инструкция:*\n"
        f"1. Откройте [@BotFather]({BOTFather_LINK})\n"
        f"2. Напишите `/newbot`\n"
        f"3. Придумайте название бота\n"
        f"4. Скопируйте полученный токен\n\n"
        f"🔑 *Формат токена:* `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`\n\n"
        f"Отправьте токен следующим сообщением:"
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=create_back_button("my_bots")
    )

    await state.set_state(ConnectBotStates.waiting_for_token)
    await callback.answer()


@router.message(ConnectBotStates.waiting_for_token)
async def process_bot_token(
    message: Message,
    state: FSMContext
) -> None:
    """Process bot token from user"""
    from src.utils.repositories import get_master_repo, get_bot_repo, get_subscription_repo

    master_repo = get_master_repo()
    bot_repo = get_bot_repo()
    subscription_repo = get_subscription_repo()

    token = message.text.strip()

    # Validate token format
    if not re.match(BOT_TOKEN_PATTERN, token):
        await message.answer(
            "❌ Неверный формат токена\n\n"
            "Токен должен выглядеть так:\n"
            "123456789:ABCdefGHIjklMNOpqrsTUVwxyz\n\n"
            f"Получите токен у @BotFather"
        )
        return

    # Get master
    master = await master_repo.get_master_by_telegram_id(message.from_user.id)
    if not master:
        await message.answer("❌ Ошибка: пользователь не найден. Напишите /start")
        await state.clear()
        return

    # Check subscription limits
    can_create = await subscription_repo.can_create_bot(master['id'])
    if not can_create:
        await message.answer(
            "❌ Достигнут лимит ботов\n\n"
            "Ваш тариф позволяет создать только 1 бота.\n"
            "Для большего количества ботов оформите подписку Pro или Business.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        return

    try:
        # Verify token with Telegram API
        bot_info = await verify_bot_token(token)

        if not bot_info:
            await message.answer(
                "❌ Недействительный токен\n\n"
                "Токен не прошёл проверку. Проверьте правильность токена "
                "у @BotFather и попробуйте снова."
            )
            return

        # Check if bot already exists
        existing_bot = await bot_repo.get_bot_by_username(bot_info['username'])
        if existing_bot:
            await message.answer(
                f"❌ Бот @{bot_info['username']} уже добавлен в систему.",
                reply_markup=get_main_menu_keyboard()
            )
            await state.clear()
            return

        # Save token and bot info to state
        await state.update_data(
            token=token,
            bot_username=bot_info['username'],
            bot_first_name=bot_info.get('first_name', '')
        )

        # Ask for bot name
        await message.answer(
            f"✅ Токен принят!\n\n"
            f"🤖 Бот: @{bot_info['username']}\n"
            f"📝 Имя: {bot_info.get('first_name', 'Нет')}\n\n"
            f"Теперь введите название для вашего бота "
            f"(как он будет отображаться в меню):\n\n"
            f"Например: Мой Салон, Барбершоп Иван и т.д."
        )

        await state.set_state(ConnectBotStates.waiting_for_bot_name)

    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        await message.answer(
            "❌ Ошибка при проверке токена. Попробуйте позже."
        )
        await state.clear()


@router.message(ConnectBotStates.waiting_for_bot_name)
async def process_bot_name(
    message: Message,
    state: FSMContext
) -> None:
    """Process bot name and create bot"""
    from src.utils.repositories import get_master_repo, get_bot_repo

    master_repo = get_master_repo()
    bot_repo = get_bot_repo()

    bot_name = message.text.strip()

    if len(bot_name) < 2 or len(bot_name) > 50:
        await message.answer(
            "❌ Название должно содержать от 2 до 50 символов. Попробуйте снова:"
        )
        return

    try:
        data = await state.get_data()
        token = data['token']
        bot_username = data['bot_username']

        # Encrypt token
        encrypted_token = encrypt_token(token)

        # Get master
        master = await master_repo.get_master_by_telegram_id(message.from_user.id)
        if not master:
            await message.answer("❌ Ошибка: пользователь не найден")
            await state.clear()
            return

        # Create bot in database
        bot_id = await bot_repo.create_bot(
            master_id=master['id'],
            bot_token=encrypted_token,
            bot_username=bot_username,
            bot_name=bot_name
        )

        # Call Factory Service to create container
        try:
            container_info = await trigger_bot_creation(str(bot_id), token)
            if container_info:
                logger.info(f"Container created: {container_info.get('container_id')}")
                await bot_repo.update_bot_container(
                    bot_id,
                    container_info.get('container_id'),
                    "creating"
                )
            else:
                logger.warning(f"Failed to create container for bot {bot_id}")
                await bot_repo.update_bot_container(bot_id, None, "error")
        except Exception as e:
            logger.error(f"Error creating container: {e}")
            await bot_repo.update_bot_container(bot_id, None, "error")

        await message.answer(
            "✅ *Бот успешно создан!*\n\n"
            f"🤖 @{bot_username}\n"
            f"📝 {bot_name}\n\n"
            "✨ Контейнер бота создаётся...\n\n"
            "Это может занять 1-2 минуты. "
            "Бот появится в списке ваших ботов.",
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard()
        )

        logger.info(f"Bot {bot_id} (@{bot_username}) created by user {message.from_user.id}")

        await state.clear()

    except Exception as e:
        logger.error(f"Error creating bot: {e}")
        await message.answer(
            "❌ Ошибка при создании бота. Попробуйте позже."
        )
        await state.clear()


@router.callback_query(F.data.startswith("bot_menu:"))
async def show_bot_menu(callback: CallbackQuery) -> None:
    """Show bot management menu"""
    from src.utils.repositories import get_bot_repo

    bot_repo = get_bot_repo()

    bot_id = callback.data.split(":")[1]

    try:
        bot = await bot_repo.get_bot_by_id(bot_id)

        if not bot:
            await callback.answer("❌ Бот не найден", show_alert=True)
            return

        status_emoji = {
            'creating': '🔨',
            'running': '🟢',
            'stopped': '⏸️',
            'error': '❌',
            'restarting': '🔄'
        }.get(bot['container_status'], '❓')

        text = (
            f"🤖 *{bot.get('bot_name') or bot['bot_username']}*\n\n"
            f"@{bot['bot_username']}\n"
            f"Статус: {status_emoji} {bot['container_status']}\n\n"
            f"_{bot.get('business_name') or 'Название бизнеса не указано'}_"
        )

        keyboard = get_bot_actions_keyboard(bot_id)

        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error showing bot menu: {e}")
        await callback.answer("❌ Ошибка при загрузке меню бота", show_alert=True)


@router.callback_query(F.data.startswith("bot_schedule:"))
async def bot_manage_schedule(callback: CallbackQuery) -> None:
    """Manage bot schedule"""
    bot_id = callback.data.split(":")[1]

    # Show schedule menu with bot-specific actions
    text = (
        "📅 *Управление расписанием*\n\n"
        "Выберите действие:"
    )


    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📊 Просмотр расписания",
                callback_data=f"view_bot_schedule:{bot_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🕐 Установить рабочие часы",
                callback_data=f"set_bot_schedule:{bot_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад к боту",
                callback_data=f"bot_menu:{bot_id}"
            )
        ]
    ])

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bot_appointments:"))
async def bot_view_appointments(callback: CallbackQuery) -> None:
    """View bot appointments"""
    bot_id = callback.data.split(":")[1]

    text = (
        "📋 *Записи клиентов*\n\n"
        f"Бот ID: {bot_id[:8]}...\n\n"
        "_Загрузка записей..._\n\n"
        "Функция в разработке 🔨"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к боту", callback_data=f"bot_menu:{bot_id}")]
        ]
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bot_clients:"))
async def bot_view_clients(callback: CallbackQuery) -> None:
    """View bot clients"""
    bot_id = callback.data.split(":")[1]

    text = (
        "👥 *Клиенты*\n\n"
        f"Бот ID: {bot_id[:8]}...\n\n"
        "_Загрузка клиентов..._\n\n"
        "Функция в разработке 🔨"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к боту", callback_data=f"bot_menu:{bot_id}")]
        ]
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bot_restart:"))
async def bot_restart(callback: CallbackQuery) -> None:
    """Restart bot container"""
    bot_id = callback.data.split(":")[1]
    settings = get_settings()

    await callback.answer("🔄 Перезапуск бота...", show_alert=True)

    try:
        # Call Factory Service to restart container
        async with httpx.AsyncClient(timeout=settings.FACTORY_SERVICE_TIMEOUT) as client:
            response = await client.post(
                f"{settings.FACTORY_SERVICE_URL}/api/v1/factory/bots/{bot_id}/restart"
            )
            response.raise_for_status()
            logger.info(f"Bot {bot_id} restarted successfully")
    except Exception as e:
        logger.error(f"Error restarting bot {bot_id}: {e}")
        await callback.answer(f"❌ Ошибка перезапуска: {str(e)}", show_alert=True)
        return

    text = (
        "✅ *Бот перезапускается*\n\n"
        "Это может занять 30-60 секунд.\n\n"
        "Вы получите уведомление когда бот будет снова доступен."
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к боту", callback_data=f"bot_menu:{bot_id}")]
        ]
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("bot_stop:"))
async def bot_stop(callback: CallbackQuery) -> None:
    """Stop bot container"""
    bot_id = callback.data.split(":")[1]

    # Show confirmation
    from src.keyboards import get_confirmation_keyboard

    text = (
        "⚠️ *Остановить бота?*\n\n"
        "После остановки бот не будет отвечать на сообщения клиентов.\n\n"
        "Вы сможете запустить его снова в любое время."
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_confirmation_keyboard("stop_bot", bot_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bot_services:"))
async def bot_manage_services(callback: CallbackQuery) -> None:
    """Manage bot services"""
    from src.utils.repositories import get_bot_repo, get_service_repo

    bot_repo = get_bot_repo()
    service_repo = get_service_repo()

    bot_id = callback.data.split(":")[1]

    try:
        # Verify bot exists
        bot = await bot_repo.get_bot_by_id(bot_id)
        if not bot:
            await callback.answer("❌ Бот не найден", show_alert=True)
            return

        # Get bot services
        services = await service_repo.get_bot_services(bot_id)

        if not services:
            text = "📝 *Услуги*\n\nУ вас пока нет услуг."
        else:
            text = f"📝 *Услуги* ({len(services)})\n\nВыберите услугу для управления:"

        from src.keyboards import get_services_list_keyboard
        keyboard = get_services_list_keyboard(bot_id, services)

        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error loading services: {e}")
        await callback.answer("❌ Ошибка при загрузке услуг", show_alert=True)


@router.callback_query(F.data.startswith("confirm:stop_bot:"))
async def confirm_stop_bot(callback: CallbackQuery) -> None:
    """Confirm bot stop"""
    bot_id = callback.data.split(":")[2]
    settings = get_settings()

    try:
        # Call Factory Service to stop container
        async with httpx.AsyncClient(timeout=settings.FACTORY_SERVICE_TIMEOUT) as client:
            response = await client.post(
                f"{settings.FACTORY_SERVICE_URL}/api/v1/factory/bots/{bot_id}/stop"
            )
            response.raise_for_status()
            logger.info(f"Bot {bot_id} stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping bot {bot_id}: {e}")
        await callback.answer(f"❌ Ошибка остановки: {str(e)}", show_alert=True)
        return

    text = (
        "✅ *Бот остановлен*\n\n"
        "Клиенты не могут записываться пока бот остановлен.\n\n"
        "Нажмите *Запустить* чтобы снова активировать бота."
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="▶️ Запустить", callback_data=f"bot_start:{bot_id}")
            ],
            [
                InlineKeyboardButton(text="🔙 Назад к боту", callback_data=f"bot_menu:{bot_id}")
            ]
        ]
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bot_start:"))
async def bot_start(callback: CallbackQuery) -> None:
    """Start bot container"""
    bot_id = callback.data.split(":")[1]
    settings = get_settings()

    await callback.answer("▶️ Запуск бота...", show_alert=True)

    try:
        # Call Factory Service to start container
        async with httpx.AsyncClient(timeout=settings.FACTORY_SERVICE_TIMEOUT) as client:
            response = await client.post(
                f"{settings.FACTORY_SERVICE_URL}/api/v1/factory/bots/{bot_id}/start"
            )
            response.raise_for_status()
            logger.info(f"Bot {bot_id} started successfully")
    except Exception as e:
        logger.error(f"Error starting bot {bot_id}: {e}")
        await callback.answer(f"❌ Ошибка запуска: {str(e)}", show_alert=True)
        return

    text = (
        "✅ *Бот запускается*\n\n"
        "Это может занять 30-60 секунд.\n\n"
        "Бот скоро начнет принимать записи."
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к боту", callback_data=f"bot_menu:{bot_id}")]
        ]
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.answer()


# ============================================
# Helper Functions
# ============================================

async def verify_bot_token(token: str) -> dict:
    """
    Verify bot token with Telegram API

    Args:
        token: Bot token to verify

    Returns:
        Bot info dict if valid, None otherwise
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.telegram.org/bot{token}/getMe"
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    return data.get('result')

        return None

    except Exception as e:
        logger.error(f"Error verifying bot token: {e}")
        return None


async def trigger_bot_creation(bot_id: str, token: str) -> dict:
    """
    Trigger bot container creation via Factory Service

    Args:
        bot_id: Bot UUID
        token: Decrypted bot token

    Returns:
        Container info dict if successful, None otherwise
    """
    settings = get_settings()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.FACTORY_SERVICE_URL}/api/v1/factory/bots/",
                json={
                    "bot_id": bot_id,
                    "bot_token": token,
                    "bot_username": "",  # Will be filled by Factory Service
                },
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                logger.info(f"Bot creation triggered successfully: {bot_id}")
                return {
                    "container_id": data.get("container_id"),
                    "status": data.get("status")
                }
            else:
                logger.error(f"Failed to trigger bot creation: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error calling Factory Service: {e}")
            return None
