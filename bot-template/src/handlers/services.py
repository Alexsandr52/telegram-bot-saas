"""
Services Handlers
Show catalog, select service, select date/time
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from keyboards import get_services_keyboard, get_dates_keyboard, get_main_menu_keyboard, get_time_slots_keyboard
from utils.config import get_config_manager
from utils.db import get_database


# Event types for analytics
class ServiceEventType:
    """Service event types"""
    SERVICE_VIEWED = "service_viewed"
    DATE_SELECTED = "date_selected"


router = Router(name="services")


# ============================================
# FSM States
# ============================================

class BookingStates(StatesGroup):
    """Booking flow states"""
    selecting_service = State()
    selecting_date = State()
    selecting_time = State()
    confirming = State()


# ============================================
# Show Catalog
# ============================================

async def show_catalog(callback: CallbackQuery) -> None:
    """Show services catalog"""
    config_manager = get_config_manager()
    db = get_database()

    if not config_manager or not db:
        await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
        return

    # Get active services
    services = await db.get_active_services()

    if not services:
        await callback.message.edit_text(
            "😔 Услуг пока нет. Попробуйте позже.",
            reply_markup=get_main_menu_keyboard(config_manager.config.custom_commands)
        )
        await callback.answer()
        return

    # Show services
    await callback.message.edit_text(
        "📋 *Наши услуги:*\n\n"
        "Выберите услугу для записи:",
        parse_mode="Markdown",
        reply_markup=get_services_keyboard(services)
    )
    await callback.answer()

    logger.info(f"User {callback.from_user.id} viewed catalog")


@router.callback_query(F.data == "catalog")
async def cmd_catalog(callback: CallbackQuery) -> None:
    """Handle /catalog command callback"""
    await show_catalog(callback)


@router.callback_query(F.data.startswith("service_"))
async def service_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Handle service selection
    Show date selection keyboard
    """
    service_id = callback.data.split("_")[1]
    config_manager = get_config_manager()
    db = get_database()

    # Get service info
    service = await db.get_service(service_id)

    if not service:
        await callback.answer("❌ Услуга не найдена", show_alert=True)
        return

    # Save service_id to state
    await state.update_data(service_id=service_id, service_name=service['name'])

    # Log analytics event
    await db.log_analytics_event(
        ServiceEventType.SERVICE_VIEWED,
        user_id=callback.from_user.id,
        event_data={
            'service_id': service_id,
            'service_name': service['name'],
            'price': float(service['price'])
        }
    )

    # Show date selection
    await callback.message.edit_text(
        f"✅ Выбрана услуга: *{service['name']}*\n\n"
        f"💰 Цена: {service['price']}₽\n"
        f"⏱️ Длительность: {service['duration_minutes']} мин\n\n"
        f"Выберите дату:",
        parse_mode="Markdown",
        reply_markup=get_dates_keyboard(days=7)
    )

    await state.set_state(BookingStates.selecting_date)
    await callback.answer()

    logger.info(f"User {callback.from_user.id} selected service {service['name']}")


@router.callback_query(F.data.startswith("date_"), BookingStates.selecting_date)
async def date_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Handle date selection
    Show available time slots
    """
    date_str = callback.data.split("_")[1]

    from datetime import datetime
    selected_date = datetime.fromisoformat(date_str)

    # Get service_id from state
    data = await state.get_data()
    service_id = data['service_id']

    # Save date to state
    await state.update_data(selected_date=selected_date)

    db = get_database()

    # Log analytics event
    await db.log_analytics_event(
        ServiceEventType.DATE_SELECTED,
        user_id=callback.from_user.id,
        event_data={
            'service_id': service_id,
            'date': date_str
        }
    )

    # Get available slots
    slots = await db.get_available_slots(service_id, selected_date)

    # Format date for display
    day_names = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    date_display = f"{selected_date.strftime('%d.%m.%Y')} ({day_names[selected_date.weekday()]})"

    await callback.message.edit_text(
        f"📅 {date_display}\n\n"
        f"Выберите удобное время:",
        reply_markup=get_time_slots_keyboard(slots, date_str, service_id)
    )

    await state.set_state(BookingStates.selecting_time)
    await callback.answer()

    logger.info(f"User {callback.from_user.id} selected date {date_str}")


@router.callback_query(F.data == "select_date")
async def back_to_dates(callback: CallbackQuery, state: FSMContext) -> None:
    """Return to date selection"""
    await callback.message.edit_text(
        "📅 Выберите другую дату:",
        reply_markup=get_dates_keyboard(days=7)
    )

    await state.set_state(BookingStates.selecting_date)
    await callback.answer()
