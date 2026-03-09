"""
Connect bot handler for Platform Bot
Handles bot token registration and container creation
"""
import re
import httpx
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
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
async def show_my_bots(
    callback: CallbackQuery,
    master_repo: MasterRepository,
    bot_repo: BotRepository
) -> None:
    """Show user's bots or prompt to add new bot"""
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
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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
    state: FSMContext,
    master_repo: MasterRepository,
    bot_repo: BotRepository,
    subscription_repo: SubscriptionRepository
) -> None:
    """Process bot token from user"""
    token = message.text.strip()

    # Validate token format
    if not re.match(BOT_TOKEN_PATTERN, token):
        await message.answer(
            "❌ *Неверный формат токена*\n\n"
            f"Токен должен выглядеть так:\n"
            "`123456789:ABCdefGHIjklMNOpqrsTUVwxyz`\n\n"
            f"Получите токен у [@BotFather]({BOTFather_LINK})",
            parse_mode="Markdown"
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
            "❌ *Достигнут лимит ботов*\n\n"
            "Ваш тариф позволяет создать только 1 бота.\n"
            "Для большего количества ботов оформите подписку Pro или Business.",
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        return

    try:
        # Verify token with Telegram API
        bot_info = await verify_bot_token(token)

        if not bot_info:
            await message.answer(
                "❌ *Недействительный токен*\n\n"
                "Токен не прошёл проверку. Проверьте правильность токена "
                f"у [@BotFather]({BOTFather_LINK}) и попробуйте снова.",
                parse_mode="Markdown"
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
            f"🤖 *Бот:* @{bot_info['username']}\n"
            f"📝 *Имя:* {bot_info.get('first_name', 'Нет')}\n\n"
            f"Теперь введите название для вашего бота "
            f"(как он будет отображаться в меню):\n\n"
            f"_Например: Мой Салон, Барбершоп Иван и т.д._",
            parse_mode="Markdown"
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
    state: FSMContext,
    master_repo: MasterRepository,
    bot_repo: BotRepository
) -> None:
    """Process bot name and create bot"""
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

        # TODO: Call Factory Service to create container
        # For now, just mark as running
        await bot_repo.update_bot_container(bot_id, "pending", "creating")

        await message.answer(
            "✅ *Бот успешно создан!*\n\n"
            f"🤖 @{bot_username}\n"
            f"📝 {bot_name}\n\n"
            "_Контейнер бота создаётся..._\n\n"
            "Это может занять 1-2 минуты. "
            "Вы получите уведомление когда бот будет готов.",
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard()
        )

        logger.info(f"Bot {bot_id} (@{bot_username}) created by user {message.from_user.id}")

        # TODO: Trigger async container creation via Factory Service
        # await trigger_bot_creation(bot_id, token)

        await state.clear()

    except Exception as e:
        logger.error(f"Error creating bot: {e}")
        await message.answer(
            "❌ Ошибка при создании бота. Попробуйте позже."
        )
        await state.clear()


@router.callback_query(F.data.startswith("bot_menu:"))
async def show_bot_menu(
    callback: CallbackQuery,
    bot_repo: BotRepository
) -> None:
    """Show bot management menu"""
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


async def trigger_bot_creation(bot_id: str, token: str) -> None:
    """
    Trigger bot container creation via Factory Service

    TODO: Implement this when Factory Service is ready
    """
    settings = get_settings()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.FACTORY_SERVICE_URL}/api/v1/factory/bots/",
                json={
                    "bot_id": str(bot_id),
                    "bot_token": token
                },
                timeout=30.0
            )

            if response.status_code == 200:
                logger.info(f"Bot creation triggered: {bot_id}")
            else:
                logger.error(f"Failed to trigger bot creation: {response.status_code}")

        except Exception as e:
            logger.error(f"Error calling Factory Service: {e}")
