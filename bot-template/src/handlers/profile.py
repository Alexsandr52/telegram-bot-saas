"""
Profile Handlers
Show user profile and appointments
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger

from src.keyboards import get_profile_keyboard, get_main_menu_keyboard
from src.utils.config import get_config_manager
from src.utils.db import get_database

router = Router(name="profile")


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

    # Format profile info
    name = f"{client['first_name']} {client.get('last_name', '')}".strip()
    phone = client.get('phone', 'не указан')
    visits = client.get('total_visits', 0)
    spent = float(client.get('total_spent', 0))

    text = (
        f"👤 *Ваш профиль*\n\n"
        f"Имя: {name}\n"
        f"Телефон: {phone}\n"
        f"Визитов: {visits}\n"
        f"Потрачено: {spent:.0f}₽\n\n"
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_profile_keyboard()
    )
    await callback.answer()

    logger.info(f"User {callback.from_user.id} viewed profile")


@router.callback_query(F.data == "my_appointments")
async def show_my_appointments(callback: CallbackQuery) -> None:
    """Show user's appointments"""
    config_manager = get_config_manager()
    db = get_database()

    if not config_manager or not db:
        await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
        return

    # Get client
    client = await db.get_or_create_client(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name
    )

    # Get appointments
    appointments = await db.get_client_appointments(
        client_id=str(client['id']),
        limit=10
    )

    if not appointments:
        text = "📋 *Мои записи*\n\nУ вас пока нет записей."
    else:
        text = "📋 *Мои записи*\n\n"

        for appt in appointments:
            from datetime import datetime
            day_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

            appt_date = appt['start_time']
            date_str = f"{appt_date.strftime('%d.%m.%Y')} ({day_names[appt_date.weekday()]})"
            time_str = f"{appt_date.strftime('%H:%M')}"

            status_emoji = {
                'pending': '⏳',
                'confirmed': '✅',
                'completed': '✅',
                'cancelled': '❌'
            }.get(appt['status'], '❓')

            text += (
                f"{status_emoji} *{appt['service_name']}*\n"
                f"{date_str} в {time_str}\n"
                f"{appt['price']}₽\n\n"
            )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_profile_keyboard()
    )
    await callback.answer()

    logger.info(f"User {callback.from_user.id} viewed appointments")
