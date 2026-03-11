"""
Booking Handlers
Handle time slot selection and appointment confirmation
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from loguru import logger

from keyboards import get_confirmation_keyboard, get_main_menu_keyboard
from utils.config import get_config_manager
from utils.db import get_database
from handlers.services import BookingStates


router = Router(name="booking")


@router.callback_query(F.data.startswith("slot_"), BookingStates.selecting_time)
async def time_slot_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Handle time slot selection
    Show confirmation
    """
    # Parse slot data
    _, start_time_str, end_time_str = callback.data.split("_")
    from datetime import datetime

    start_time = datetime.fromisoformat(start_time_str)
    end_time = datetime.fromisoformat(end_time_str)

    # Get data from state
    data = await state.get_data()
    service_id = data['service_id']
    service_name = data['service_name']
    selected_date = data['selected_date']

    # Save times to state
    await state.update_data(
        selected_start_time=start_time,
        selected_end_time=end_time
    )

    # Get service price
    db = get_database()
    service = await db.get_service(service_id)

    # Format for display
    day_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    date_str = f"{selected_date.strftime('%d.%m.%Y')} ({day_names[selected_date.weekday()]})"
    time_str = f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"

    # Show confirmation
    await callback.message.edit_text(
        f"📋 *Подтверждение записи*\n\n"
        f"Услуга: {service_name}\n"
        f"Дата: {date_str}\n"
        f"Время: {time_str}\n"
        f"Стоимость: {service['price']}₽\n\n"
        f"Подтвердите запись:",
        parse_mode="Markdown",
        reply_markup=get_confirmation_keyboard(
            service_name,
            date_str,
            time_str,
            float(service['price'])
        )
    )

    await state.set_state(BookingStates.confirming)
    await callback.answer()

    logger.info(f"User {callback.from_user.id} selected time slot {start_time}")


@router.callback_query(F.data == "confirm_booking", BookingStates.confirming)
async def confirm_booking(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Confirm and create appointment
    """
    from datetime import datetime
    from decimal import Decimal

    config_manager = get_config_manager()
    db = get_database()

    # Get data from state
    data = await state.get_data()
    service_id = data['service_id']
    start_time = data['selected_start_time']
    end_time = data['selected_end_time']

    # Get or create client
    client = await db.get_or_create_client(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name
    )

    # Get service price
    service = await db.get_service(service_id)
    price = Decimal(str(service['price']))

    # Create appointment
    try:
        appointment_id = await db.create_appointment(
            client_id=str(client['id']),
            service_id=service_id,
            start_time=start_time,
            end_time=end_time,
            price=price
        )

        # Format confirmation message
        day_names = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
        date_str = f"{start_time.strftime('%d.%m.%Y')} ({day_names[start_time.weekday()]})"
        time_str = f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"

        await callback.message.edit_text(
            f"✅ *Запись создана!*\n\n"
            f"🎉 Вы записаны на {service['name']}\n\n"
            f"📅 Дата: {date_str}\n"
            f"🕐 Время: {time_str}\n"
            f"💰 Стоимость: {price}₽\n\n"
            f"📝 Номер записи: {appointment_id}\n\n"
            f"До встречи!",
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard(config_manager.config.custom_commands)
        )

        logger.info(f"Appointment {appointment_id} created for user {callback.from_user.id}")

    except Exception as e:
        logger.error(f"Error creating appointment: {e}")
        await callback.message.edit_text(
            "😔 Произошла ошибка при создании записи. Попробуйте позже.",
            reply_markup=get_main_menu_keyboard(config_manager.config.custom_commands)
        )

    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "no_slots")
async def no_available_slots(callback: CallbackQuery) -> None:
    """Handle case when no slots available"""
    await callback.answer("😔 Нет доступных слотов на эту дату", show_alert=True)
