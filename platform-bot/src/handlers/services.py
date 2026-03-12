"""
Services Handler for Platform Bot
Handles CRUD operations for bot services
"""
import re
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from src.utils.repositories import get_bot_repo, get_service_repo
from src.keyboards import (
    create_back_button,
    get_bot_actions_keyboard,
    get_services_list_keyboard,
    get_service_management_keyboard
)


router = Router(name="services_handler")


# ============================================
# FSM States
# ============================================

class ServiceStates(StatesGroup):
    """States for service management flow"""
    waiting_for_name = State()
    waiting_for_price = State()
    waiting_for_duration = State()
    waiting_for_description = State()


# ============================================
# Services List
# ============================================

@router.callback_query(F.data.startswith("bot_services:"))
async def show_services(callback: CallbackQuery) -> None:
    """Show services list for a bot"""
    bot_repo = get_bot_repo()
    bot_id = callback.data.split(":")[1]

    try:
        # Verify bot ownership
        bot = await bot_repo.get_bot_by_id(bot_id)
        if not bot:
            await callback.answer("❌ Бот не найден", show_alert=True)
            return

        # Get services
        service_repo = get_service_repo()
        services = await service_repo.get_bot_services(bot_id)

        if not services:
            text = (
                "📋 *Услуги*\n\n"
                "У вас пока нет добавленных услуг.\n\n"
                "Нажмите *➕ Добавить услугу* чтобы создать первую."
            )
        else:
            text = "📋 *Ваши услуги*\n\n"
            for svc in services:
                status = "✅" if svc['is_active'] else "❌"
                text += (
                    f"{status} *{svc['name']}*\n"
                    f"💰 {svc['price']}₽ | ⏱️ {svc['duration_minutes']} мин\n"
                    f"ID: `{svc['id']}`\n\n"
                )

        keyboard = get_services_list_keyboard(bot_id, services)

        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error showing services: {e}")
        await callback.answer("❌ Ошибка при загрузке услуг", show_alert=True)


# ============================================
# Create Service
# ============================================

@router.callback_query(F.data.startswith("add_service:"))
async def start_add_service(callback: CallbackQuery, state: FSMContext) -> None:
    """Start add service flow"""
    bot_id = callback.data.split(":")[1]

    await state.update_data(bot_id=bot_id)

    await callback.message.edit_text(
        "➕ *Новая услуга*\n\n"
        "Введите название услуги:\n\n"
        "_Например: Мужская стрижка, Маникюр, Массаж_",
        parse_mode="Markdown",
        reply_markup=create_back_button(f"bot_services:{bot_id}")
    )

    await state.set_state(ServiceStates.waiting_for_name)
    await callback.answer()


@router.message(ServiceStates.waiting_for_name)
async def process_service_name(message: Message, state: FSMContext) -> None:
    """Process service name"""
    name = message.text.strip()

    if len(name) < 2 or len(name) > 100:
        await message.answer(
            "❌ Название должно содержать от 2 до 100 символов. Попробуйте снова:"
        )
        return

    await state.update_data(name=name)

    await message.answer(
        f"✅ Название: *{name}*\n\n"
        "💰 *Введите цену услуги в рублях:*",
        parse_mode="Markdown"
    )

    await state.set_state(ServiceStates.waiting_for_price)


@router.message(ServiceStates.waiting_for_price)
async def process_service_price(message: Message, state: FSMContext) -> None:
    """Process service price"""
    price_text = message.text.strip()

    # Extract digits
    price_match = re.search(r'\d+', price_text)
    if not price_match:
        await message.answer(
            "❌ Неверный формат цены. Введите число (например: 1500 или 1500₽):"
        )
        return

    price = float(price_match.group())

    if price < 0 or price > 100000:
        await message.answer(
            "❌ Цена должна быть от 0 до 100000 ₽. Попробуйте снова:"
        )
        return

    await state.update_data(price=price)

    await message.answer(
        f"✅ Цена: {price}₽\n\n"
        "⏱️ *Введите длительность услуги в минутах:*",
        parse_mode="Markdown"
    )

    await state.set_state(ServiceStates.waiting_for_duration)


@router.message(ServiceStates.waiting_for_duration)
async def process_service_duration(message: Message, state: FSMContext) -> None:
    """Process service duration"""
    duration_text = message.text.strip()

    # Extract digits
    duration_match = re.search(r'\d+', duration_text)
    if not duration_match:
        await message.answer(
            "❌ Неверный формат. Введите число (например: 60):"
        )
        return

    duration = int(duration_match.group())

    if duration < 5 or duration > 480:
        await message.answer(
            "❌ Длительность должна быть от 5 до 480 минут (8 часов). Попробуйте снова:"
        )
        return

    await state.update_data(duration_minutes=duration)

    await message.answer(
        f"✅ Длительность: {duration} мин\n\n"
        "📝 *Введите описание услуги (необязательно):*\n\n"
        "Отправьте описание или /skip чтобы пропустить",
        parse_mode="Markdown"
    )

    await state.set_state(ServiceStates.waiting_for_description)


@router.message(ServiceStates.waiting_for_description)
async def process_service_description(message: Message, state: FSMContext) -> None:
    """Process service description"""
    description = message.text.strip() if message.text else None

    await state.update_data(description=description)

    # Get all data
    data = await state.get_data()
    bot_id = data['bot_id']
    name = data['name']
    price = data['price']
    duration_minutes = data['duration_minutes']

    try:
        # Create service
        service_repo = get_service_repo()
        service_id = await service_repo.create_service(
            bot_id=bot_id,
            name=name,
            price=price,
            duration_minutes=duration_minutes,
            description=description
        )

        await message.answer(
            "✅ *Услуга успешно создана!*\n\n"
            f"📝 {name}\n"
            f"💰 {price}₽\n"
            f"⏱️ {duration_minutes} мин\n"
            f"📋 {description or 'Без описания'}\n\n"
            f"ID: `{service_id}`",
            parse_mode="Markdown",
            reply_markup=create_back_button(f"bot_services:{bot_id}")
        )

        logger.info(f"Service {service_id} created for bot {bot_id}")

    except Exception as e:
        logger.error(f"Error creating service: {e}")
        await message.answer(
            "❌ Ошибка при создании услуги. Попробуйте позже."
        )

    await state.clear()


# ============================================
# Edit Service
# ============================================

@router.callback_query(F.data.startswith("edit_service:"))
async def start_edit_service(callback: CallbackQuery, state: FSMContext) -> None:
    """Show edit options for a service"""
    service_id = callback.data.split(":")[1]

    try:
        service_repo = get_service_repo()
        service = await service_repo.get_service(service_id)
        if not service:
            await callback.answer("❌ Услуга не найдена", show_alert=True)
            return

        text = (
            f"✏️ *Редактирование услуги*\n\n"
            f"📝 *{service['name']}*\n"
            f"💰 {service['price']}₽\n"
            f"⏱️ {service['duration_minutes']} мин\n"
            f"📋 {service['description'] or 'Без описания'}\n\n"
            f"Выберите, что изменить:"
        )

        keyboard = get_service_management_keyboard(service_id)

        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error loading service: {e}")
        await callback.answer("❌ Ошибка при загрузке услуги", show_alert=True)


@router.callback_query(F.data.startswith("service_toggle_active:"))
async def toggle_service_active(callback: CallbackQuery) -> None:
    """Toggle service active status"""
    service_id = callback.data.split(":")[1]

    try:
        service_repo = get_service_repo()
        service = await service_repo.get_service(service_id)
        if not service:
            await callback.answer("❌ Услуга не найдена", show_alert=True)
            return

        new_status = not service['is_active']
        await service_repo.update_service(service_id, is_active=new_status)

        status_text = "активна" if new_status else "скрыта"
        await callback.answer(f"✅ Услуга {status_text}")

    except Exception as e:
        logger.error(f"Error toggling service: {e}")
        await callback.answer("❌ Ошибка при изменении статуса", show_alert=True)


@router.callback_query(F.data.startswith("delete_service:"))
async def confirm_delete_service(callback: CallbackQuery) -> None:
    """Confirm service deletion"""
    service_id = callback.data.split(":")[1]

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_service:{service_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_service:{service_id}")
        ]
    ])

    await callback.message.edit_text(
        "⚠️ *Удаление услуги*\n\n"
        "Вы уверены, что хотите удалить эту услугу?\n\n"
        "Услуга будет скрыта, но не удалена из базы данных.",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_service:"))
async def delete_service(callback: CallbackQuery) -> None:
    """Delete a service"""
    service_id = callback.data.split(":")[1]

    try:
        service_repo = get_service_repo()
        await service_repo.delete_service(service_id)
        await callback.answer("✅ Услуга удалена")

    except Exception as e:
        logger.error(f"Error deleting service: {e}")
        await callback.answer("❌ Ошибка при удалении услуги", show_alert=True)
