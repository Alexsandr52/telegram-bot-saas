"""
Booking Handlers
Handle time slot selection and appointment confirmation
"""
import httpx
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from loguru import logger

from keyboards import get_confirmation_keyboard, get_main_menu_keyboard
from utils.config import get_config_manager
from utils.db import get_database
from handlers.services import BookingStates


router = Router(name="booking")


async def notify_master_new_appointment(
    appointment_id: str,
    service_name: str,
    start_time,
    end_time,
    price,
    client: dict,
    bot_token: str
):
    """Send notification to master about new appointment"""
    try:
        db = get_database()
        logger.info(f"Attempting to notify master about appointment {appointment_id}, bot_id: {db.bot_id}")

        # Get master_telegram_id from bots table
        bot_info = await db.fetchrow(
            "SELECT master_telegram_id FROM bots WHERE id = $1",
            str(db.bot_id)
        )

        if not bot_info:
            logger.error(f"Bot not found: bot_id={db.bot_id}")
            return

        if not bot_info['master_telegram_id']:
            logger.error(f"master_telegram_id is NULL for bot {db.bot_id}")
            return

        master_telegram_id = bot_info['master_telegram_id']
        logger.info(f"Found master_telegram_id: {master_telegram_id}")

        # Format message
        day_names = ['Понедельник', 'Вторник', 'Среду', 'Четверг', 'Пятницу', 'Субботу', 'Воскресенье']
        date_str = start_time.strftime('%d.%m.%Y')
        weekday = day_names[start_time.weekday()]
        time_str = f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"

        client_link = f"tg://user?id={client.get('telegram_id')}" if client.get('telegram_id') else None

        message = (
            f"🔔 *Новая запись!*\n\n"
            f"🎉 *Услуга:* {service_name}\n"
            f"👤 *Клиент:* {client.get('first_name', 'Клиент')} {client.get('last_name', '')}\n"
            f"📅 *Дата:* {date_str} ({weekday})\n"
            f"🕐 *Время:* {time_str}\n"
            f"💰 *Цена:* {price}₽\n\n"
        )

        if client_link:
            message += f"📱 [Связаться с клиентом]({client_link})\n\n"

        message += f"ID: {appointment_id[:8]}..."

        # Create inline keyboard for confirmation
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"master_confirm_{appointment_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"master_reject_{appointment_id}")
            ]
        ])

        # Add contact buttons if available
        contact_row = []
        if client_link:
            contact_row.append(InlineKeyboardButton(text="👤 Связаться", url=client_link))
        if client.get('username'):
            contact_row.append(InlineKeyboardButton(text="💬 Чат", url=f"https://t.me/{client.get('username')}"))

        if contact_row:
            keyboard.inline_keyboard.append(contact_row)

        # Send message via Telegram Bot API
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": master_telegram_id,
            "text": message,
            "parse_mode": "Markdown",
            "reply_markup": keyboard.to_json()
        }

        logger.info(f"Sending notification to master {master_telegram_id}")
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(url, json=payload, timeout=10.0)
            if response.status_code == 200:
                logger.info(f"✅ Master notified about appointment {appointment_id}")
            else:
                logger.error(f"❌ Failed to notify master: {response.status_code} - {response.text}")

    except Exception as e:
        logger.exception(f"Error notifying master: {e}")


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

        # Notify master about new appointment
        await notify_master_new_appointment(
            appointment_id=appointment_id,
            service_name=service['name'],
            start_time=start_time,
            end_time=end_time,
            price=price,
            client=client,
            bot_token=config_manager.config.bot_token
        )

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
