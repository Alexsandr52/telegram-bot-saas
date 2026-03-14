"""
Profile Handlers
Show user profile, appointments history, and manage appointments
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
from datetime import datetime

from keyboards import (
    get_profile_keyboard,
    get_appointments_keyboard,
    get_appointments_list_keyboard,
    get_appointment_detail_keyboard,
    get_cancel_confirmation_keyboard,
    get_main_menu_keyboard
)
from utils.config import get_config_manager
from utils.db import get_database


router = Router(name="profile")


# ============================================
# FSM States
# ============================================

class ProfileStates(StatesGroup):
    """Profile management states"""
    editing_phone = State()


# Store pagination state
class PaginationState:
    """Simple pagination state storage"""
    def __init__(self):
        self.current_page = 0
        self.list_type = "upcoming"  # or "past"


_pagination_state = {}


def get_pagination_state(user_id: int) -> PaginationState:
    """Get or create pagination state for user"""
    if user_id not in _pagination_state:
        _pagination_state[user_id] = PaginationState()
    return _pagination_state[user_id]


# ============================================
# Profile
# ============================================

@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery) -> None:
    """Show user profile"""
    config_manager = get_config_manager()
    db = get_database()

    if not config_manager or not db:
        await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
        return

    # Get or create client
    client = await db.get_or_create_client(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name
    )

    # Get upcoming appointments count
    upcoming = await db.get_upcoming_appointments(
        client_id=str(client['id']),
        limit=100
    )

    # Format profile info
    name = f"{client['first_name']} {client.get('last_name', '')}".strip()
    phone = client.get('phone', 'не указан')
    if phone == 'не указан' or not phone:
        phone = 'не указан 🔔'
    visits = client.get('total_visits', 0)
    spent = float(client.get('total_spent', 0))

    text = (
        f"👤 *Ваш профиль*\n\n"
        f"🆔 Имя: {name}\n"
        f"📱 Телефон: {phone}\n"
        f"📊 Посещений: {visits}\n"
        f"💰 Потрачено: {spent:.0f}₽\n"
        f"📅 Предстоящих записей: {len(upcoming)}\n\n"
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_profile_keyboard()
    )
    await callback.answer()

    logger.info(f"User {callback.from_user.id} viewed profile")


# ============================================
# Phone Edit
# ============================================

@router.callback_query(F.data == "edit_phone")
async def edit_phone_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Start phone editing"""
    await callback.message.edit_text(
        "📱 *Изменение номера телефона*\n\n"
        "Пожалуйста, введите ваш номер телефона в формате:\n"
        "`+7XXXYYYZZZZ` или `8XXXYYYZZZZ`\n\n"
        "Или нажмите кнопку ниже, чтобы отправить контакт из Telegram:",
        parse_mode="Markdown",
        reply_markup=get_phone_request_keyboard()
    )

    await state.set_state(ProfileStates.editing_phone)
    await callback.answer()


@router.message(ProfileStates.editing_phone)
async def edit_phone_process(message: Message, state: FSMContext) -> None:
    """Process phone number input"""
    db = get_database()
    if not db:
        await message.answer("❌ Ошибка базы данных")
        await state.clear()
        return

    # Get client
    client = await db.get_or_create_client(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )

    phone = None

    # Check if contact was sent
    if message.contact:
        phone = message.contact.phone_number
    elif message.text:
        phone = message.text.strip()

    # Validate and clean phone
    if phone:
        # Remove all non-digit characters
        phone_digits = ''.join(c for c in phone if c.isdigit())

        # Validate length (Russian numbers: 10 or 11 digits)
        if len(phone_digits) in [10, 11]:
            # Format to standard format
            if len(phone_digits) == 10:
                phone_digits = '7' + phone_digits
            elif phone_digits[0] == '8':
                phone_digits = '7' + phone_digits[1:]

            phone = f"+{phone_digits[0]} {phone_digits[1:4]} {phone_digits[4:7]} {phone_digits[7:9]} {phone_digits[9:]}"

            # Update in database
            await db.update_client_phone(str(client['id']), phone)

            await message.answer(
                f"✅ Номер телефона сохранён:\n`{phone}`",
                parse_mode="Markdown",
                reply_markup=get_remove_keyboard()
            )

            # Show profile again
            config_manager = get_config_manager()
            await message.answer(
                "👤 Ваш профиль обновлён!",
                reply_markup=get_main_menu_keyboard(config_manager.config.custom_commands)
            )

            logger.info(f"User {message.from_user.id} updated phone: {phone}")
        else:
            await message.answer(
                "❌ Неверный формат номера. Пожалуйста, введите номер в формате "
                "`+7XXXXXXXXXX` или `8XXXXXXXXXX` (10 или 11 цифр)",
                parse_mode="Markdown"
            )
            return

    await state.clear()


# ============================================
# Appointments List
# ============================================

@router.callback_query(F.data == "my_appointments")
async def show_my_appointments(callback: CallbackQuery) -> None:
    """Show appointments type selection"""
    await callback.message.edit_text(
        "📋 *Мои записи*\n\n"
        "Выберите тип записей:",
        parse_mode="Markdown",
        reply_markup=get_appointments_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("appointments_upcoming"))
async def show_upcoming_appointments(callback: CallbackQuery) -> None:
    """Show upcoming appointments"""
    db = get_database()
    if not db:
        await callback.answer("❌ Ошибка базы данных", show_alert=True)
        return

    # Get client
    client = await db.get_or_create_client(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name
    )

    # Get pagination state
    page_data = callback.data.split("_")
    page = int(page_data[2]) if len(page_data) > 2 else 0
    pagination = get_pagination_state(callback.from_user.id)
    pagination.current_page = page
    pagination.list_type = "upcoming"

    limit = 5
    offset = page * limit

    # Get upcoming appointments
    appointments = await db.get_upcoming_appointments(
        client_id=str(client['id']),
        limit=limit
    )

    # Check if there are more
    has_more = len(appointments) == limit

    if not appointments:
        text = "📋 *Предстоящие записи*\n\nУ вас пока нет предстоящих записей."

        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_appointments_keyboard()
        )
    else:
        text = f"📋 *Предстоящие записи* (стр. {page + 1})\n\n"

        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_appointments_list_keyboard(
                appointments=appointments,
                current_page=page,
                has_more=has_more,
                list_type="upcoming"
            )
        )

    await callback.answer()
    logger.info(f"User {callback.from_user.id} viewed upcoming appointments, page {page}")


@router.callback_query(F.data.startswith("appointments_past"))
async def show_past_appointments(callback: CallbackQuery) -> None:
    """Show past appointments"""
    db = get_database()
    if not db:
        await callback.answer("❌ Ошибка базы данных", show_alert=True)
        return

    # Get client
    client = await db.get_or_create_client(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name
    )

    # Get pagination state
    page_data = callback.data.split("_")
    page = int(page_data[2]) if len(page_data) > 2 else 0
    pagination = get_pagination_state(callback.from_user.id)
    pagination.current_page = page
    pagination.list_type = "past"

    limit = 10
    offset = page * limit

    # Get past appointments
    appointments = await db.get_past_appointments(
        client_id=str(client['id']),
        limit=limit,
        offset=offset
    )

    # Check if there are more
    has_more = len(appointments) == limit

    if not appointments:
        text = "📜 *История записей*\n\nУ вас пока нет прошедших записей."

        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_appointments_keyboard()
        )
    else:
        text = f"📜 *История записей* (стр. {page + 1})\n\n"

        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_appointments_list_keyboard(
                appointments=appointments,
                current_page=page,
                has_more=has_more,
                list_type="past"
            )
        )

    await callback.answer()
    logger.info(f"User {callback.from_user.id} viewed past appointments, page {page}")


# ============================================
# Appointment Details
# ============================================

@router.callback_query(F.data.startswith("appointment_"))
async def show_appointment_details(callback: CallbackQuery) -> None:
    """Show appointment details"""
    db = get_database()
    if not db:
        await callback.answer("❌ Ошибка базы данных", show_alert=True)
        return

    appointment_id = callback.data.split("_")[1]

    # Get appointment details
    appointment = await db.get_appointment(appointment_id)

    if not appointment:
        await callback.answer("❌ Запись не найдена", show_alert=True)
        return

    # Format details
    day_names = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']

    start_time = appointment['start_time']
    end_time = appointment['end_time']

    date_str = f"{start_time.strftime('%d.%m.%Y')} ({day_names[start_time.weekday()]})"
    time_str = f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"

    status_emoji = {
        'pending': '⏳ Ожидает подтверждения',
        'confirmed': '✅ Подтверждена',
        'completed': '✅ Выполнена',
        'cancelled': '❌ Отменена'
    }.get(appointment['status'], '❓ Неизвестный статус')

    # Check if can be cancelled
    can_cancel = (
        appointment['status'] in ['pending', 'confirmed'] and
        start_time > datetime.now()
    )

    # Build client contact link
    client_contact = ""
    telegram_id = appointment.get('telegram_id')
    if telegram_id:
        # Create tg:// link if telegram_id exists
        client_contact = f"👤 *Клиент:* [tg://user?id={telegram_id}](tg://user?id={telegram_id})\n\n"

    text = (
        f"📋 *Детали записи*\n\n"
        f"🔹 *Услуга:* {appointment['service_name']}\n"
        f"📅 *Дата:* {date_str}\n"
        f"🕐 *Время:* {time_str}\n"
        f"⏱️ *Длительность:* {appointment['duration_minutes']} мин\n"
        f"💰 *Стоимость:* {appointment['price']}₽\n"
        f"📝 *Статус:* {status_emoji}\n\n"
        f"{client_contact}"
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_appointment_detail_keyboard(
            appointment_id=appointment_id,
            can_cancel=can_cancel
        )
    )

    await callback.answer()
    logger.info(f"User {callback.from_user.id} viewed appointment {appointment_id}")


# ============================================
# Cancel Appointment
# ============================================

@router.callback_query(F.data.startswith("cancel_appointment_"))
async def cancel_appointment_prompt(callback: CallbackQuery) -> None:
    """Show cancel confirmation"""
    appointment_id = callback.data.split("_")[2]

    await callback.message.edit_text(
        "⚠️ *Отмена записи*\n\n"
        "Вы уверены, что хотите отменить эту запись?\n\n"
        "Это действие нельзя отменить.",
        parse_mode="Markdown",
        reply_markup=get_cancel_confirmation_keyboard(appointment_id)
    )

    await callback.answer()


@router.callback_query(F.data.startswith("confirm_cancel_"))
async def confirm_cancel_appointment(callback: CallbackQuery) -> None:
    """Confirm and cancel appointment"""
    db = get_database()
    if not db:
        await callback.answer("❌ Ошибка базы данных", show_alert=True)
        return

    # Get client
    client = await db.get_or_create_client(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name
    )

    appointment_id = callback.data.split("_")[2]

    # Cancel appointment
    success = await db.cancel_appointment(
        appointment_id=appointment_id,
        client_id=str(client['id'])
    )

    if success:
        await callback.message.edit_text(
            "✅ *Запись отменена*\n\n"
            "Вы можете записаться на другую услугу в любое время.",
            parse_mode="Markdown",
            reply_markup=get_appointments_keyboard()
        )

        logger.info(f"User {callback.from_user.id} cancelled appointment {appointment_id}")
    else:
        await callback.answer(
            "❌ Не удалось отменить запись. Возможно, срок отмены истёк или запись уже отменена.",
            show_alert=True
        )

        # Refresh appointment details
        await show_appointment_details(callback)


# ============================================
# Helper Functions
# ============================================

@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery) -> None:
    """Handle no-op callbacks (like pagination page number)"""
    await callback.answer()


def get_phone_request_keyboard():
    """Import keyboard function"""
    from src.keyboards import get_phone_request_keyboard
    return get_phone_request_keyboard()


def get_remove_keyboard():
    """Import keyboard function"""
    from src.keyboards import get_remove_keyboard
    return get_remove_keyboard()
