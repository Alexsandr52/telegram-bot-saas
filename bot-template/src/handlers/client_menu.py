"""
Client Menu Handlers
Basic commands: /start, /help, /about, custom catalog command
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from loguru import logger

from src.keyboards import (
    get_main_menu_keyboard,
    get_help_keyboard,
    get_services_keyboard
)
from src.utils.config import get_config_manager


router = Router(name="client_menu")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """
    Handle /start command
    Show main menu with custom commands
    """
    config_manager = get_config_manager()
    if not config_manager:
        await message.answer("⚠️ Бот не настроен. Обратитесь к администратору.")
        return

    config = config_manager.config

    # Welcome message
    business_name = config.business_name or config.bot_name

    text = (
        f"👋 Добро пожаловать в *{business_name}*!\n\n"
        "Выберите действие в меню ниже:"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(config.custom_commands)
    )

    logger.info(f"User {message.from_user.id} started bot")


@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery) -> None:
    """Return to main menu"""
    config_manager = get_config_manager()
    config = config_manager.config
    business_name = config.business_name or config.bot_name

    await callback.message.edit_text(
        f"👋 *{business_name}*\n\n"
        "Выберите действие:",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(config.custom_commands)
    )
    await callback.answer()


@router.message(Command("help"))
@router.callback_query(F.data == "help")
async def show_help(event: Message | CallbackQuery) -> None:
    """Show help information"""
    config_manager = get_config_manager()
    config = config_manager.config

    # Get custom command names
    catalog_cmd = "catalog"
    about_cmd = "about"

    for cmd in config.custom_commands:
        if cmd['handler_type'] == 'catalog':
            catalog_cmd = cmd['command']
        elif cmd['handler_type'] == 'about':
            about_cmd = cmd['command']

    help_text = (
        f"📚 *Справка*\n\n"
        f"Доступные команды:\n"
        f"/start - Главное меню\n"
        f"/{catalog_cmd} - Услуги и запись\n"
        f"/{about_cmd} - Информация о нас\n"
        f"/help - Эта справка\n\n"
        f"💡 Для записи выберите услугу в меню и удобное время."
    )

    if isinstance(event, Message):
        await event.answer(help_text, parse_mode="Markdown", reply_markup=get_help_keyboard())
    else:
        await event.message.edit_text(help_text, parse_mode="Markdown", reply_markup=get_help_keyboard())
        await event.answer()

    logger.info(f"User {event.from_user.id if isinstance(event, Message) else event.from_user.id} viewed help")


@router.callback_query(F.data.startswith("cmd_"))
async def handle_custom_command(callback: CallbackQuery) -> None:
    """
    Handle custom commands from menu

    Format: cmd_{command_name}
    """
    config_manager = get_config_manager()
    config = config_manager.config

    command = callback.data.split("_")[1]

    # Find command config
    cmd_config = None
    for cmd in config.custom_commands:
        if cmd['command'] == command:
            cmd_config = cmd
            break

    if not cmd_config:
        await callback.answer("❌ Команда не найдена", show_alert=True)
        return

    handler_type = cmd_config['handler_type']

    # Route to appropriate handler
    if handler_type == 'catalog':
        # Import services module to avoid circular dependency
        from . import services
        await services.show_catalog(callback)
    elif handler_type == 'about':
        await show_about(callback)
    else:
        await callback.answer("⚠️ Функция в разработке", show_alert=True)


async def show_about(callback: CallbackQuery) -> None:
    """Show about/business information"""
    config_manager = get_config_manager()
    config = config_manager.config

    business_name = config.business_name or config.bot_name
    business_desc = config.business_description
    business_address = config.business_address
    business_phone = config.business_phone

    text = f"ℹ️ *О нас*\n\n"
    text += f"🏪 {business_name}\n"

    if business_desc:
        text += f"\n{business_desc}\n"

    if business_address:
        text += f"\n📍 Адрес: {business_address}"

    if business_phone:
        text += f"\n📞 Телефон: {business_phone}"

    text += "\n\nВыберите действие в меню:"

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(config.custom_commands)
    )
    await callback.answer()
