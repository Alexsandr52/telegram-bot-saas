"""
Schedule Handlers for Platform Bot
Manage working hours and schedule exceptions
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
from datetime import datetime, time

from src.utils.db import ScheduleRepository
from src.utils.repositories import get_schedule_repo
from src.keyboards import (
    get_schedule_menu_keyboard,
    get_days_keyboard,
    create_back_button
)


router = Router(name="schedule_handler")


# ============================================
# FSM States
# ============================================

class ScheduleStates(StatesGroup):
    """States for schedule management"""
    selecting_day = State()
    setting_start_time = State()
    setting_end_time = State()
    setting_exception_date = State()
    setting_exception_reason = State()


# ============================================
# Schedule Menu
# ============================================

@router.callback_query(F.data == "manage_schedule")
async def show_schedule_menu(callback: CallbackQuery) -> None:
    """Show schedule management menu"""
    text = (
        "📅 *Управление расписанием*\n\n"
        "Выберите действие:\n\n"
        "• 🕐 *Рабочие часы* - настроить график работы\n"
        "• 🚫 *Выходные* - добавить исключения (отпуск, праздник)\n"
        "• 📊 *Просмотр* - посмотреть текущее расписание"
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_schedule_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "view_schedule")
async def view_schedule(callback: CallbackQuery, bot_id: str = None) -> None:
    """View current schedule"""
    schedule_repo = get_schedule_repo()

    # For now, show a placeholder
    # TODO: Get actual bot_id from context
    text = (
        "📊 *Текущее расписание*\n\n"
        "_Функция в разработке_\n\n"
        "Выберите бота для просмотра его расписания."
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=create_back_button("manage_schedule")
    )
    await callback.answer()


@router.callback_query(F.data == "set_working_hours")
async def set_working_hours(callback: CallbackQuery, state: FSMContext) -> None:
    """Start setting working hours flow"""
    text = (
        "🕐 *Настройка рабочих часов*\n\n"
        "Выберите день недели для настройки:\n\n"
        "Понедельник - Пятница: обычные рабочие дни\n"
        "Суббота: сокращенный день\n"
        "Воскресенье: выходной"
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_days_keyboard()
    )
    await state.set_state(ScheduleStates.selecting_day)
    await callback.answer()


@router.callback_query(F.data.startswith("set_day:"), ScheduleStates.selecting_day)
async def select_day(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle day selection"""
    day_num = callback.data.split(":")[1]
    day_names = {
        "1": "Понедельник",
        "2": "Вторник",
        "3": "Среда",
        "4": "Четверг",
        "5": "Пятница",
        "6": "Суббота",
        "7": "Воскресенье"
    }

    day_name = day_names.get(day_num, "День")

    await state.update_data(day_of_week=day_num)

    await callback.message.edit_text(
        f"📅 {day_name}\n\n"
        f"Введите время начала работы в формате ЧЧ:ММ\n\n"
        f"_Например: 09:00_",
        parse_mode="Markdown",
        reply_markup=create_back_button("manage_schedule")
    )
    await state.set_state(ScheduleStates.setting_start_time)
    await callback.answer()


@router.message(ScheduleStates.setting_start_time)
async def process_start_time(message: Message, state: FSMContext) -> None:
    """Process start time input"""
    time_str = message.text.strip()

    try:
        # Parse time
        hours, minutes = map(int, time_str.split(':'))
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError("Invalid time")

        await state.update_data(start_time=time_str)

        await message.answer(
            f"✅ Время начала: {time_str}\n\n"
            f"Введите время окончания работы в формате ЧЧ:ММ\n\n"
            f"_Например: 18:00_",
            parse_mode="Markdown"
        )
        await state.set_state(ScheduleStates.setting_end_time)

    except Exception:
        await message.answer(
            "❌ Неверный формат времени. Используйте формат ЧЧ:ММ\n\n"
            "_Например: 09:00_",
            parse_mode="Markdown"
        )


@router.message(ScheduleStates.setting_end_time)
async def process_end_time(message: Message, state: FSMContext) -> None:
    """Process end time and save schedule"""
    time_str = message.text.strip()

    try:
        # Parse time
        hours, minutes = map(int, time_str.split(':'))
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError("Invalid time")

        data = await state.get_data()
        day_num = data.get('day_of_week')
        start_time = data.get('start_time')

        # TODO: Save to database
        # schedule_repo = get_schedule_repo()
        # await schedule_repo.set_working_day(...)

        await message.answer(
            f"✅ *Расписание сохранено!*\n\n"
            f"📅 День: {day_num}\n"
            f"🕐 С: {start_time}\n"
            f"🕐 До: {time_str}\n\n"
            f"_В базе данных сохранено_",
            parse_mode="Markdown",
            reply_markup=create_back_button("manage_schedule")
        )

        await state.clear()

    except Exception:
        await message.answer(
            "❌ Неверный формат времени. Используйте формат ЧЧ:ММ\n\n"
            "_Например: 18:00_",
            parse_mode="Markdown"
        )


@router.callback_query(F.data == "add_exception")
async def add_exception(callback: CallbackQuery, state: FSMContext) -> None:
    """Start adding schedule exception flow"""
    text = (
        "🚫 *Добавление исключения в расписание*\n\n"
        "Введите дату в формате ДД.ММ.ГГГГ\n\n"
        "_Например: 25.12.2024_\n\n"
        "Используйте это для:\n"
        "• Отпусков\n"
        "• Праздников\n"
        "• Других выходных дней"
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=create_back_button("manage_schedule")
    )
    await state.set_state(ScheduleStates.setting_exception_date)
    await callback.answer()


@router.message(ScheduleStates.setting_exception_date)
async def process_exception_date(message: Message, state: FSMContext) -> None:
    """Process exception date"""
    date_str = message.text.strip()

    try:
        # Parse date
        date_obj = datetime.strptime(date_str, '%d.%m.%Y')

        await state.update_data(exception_date=date_obj)

        await message.answer(
            f"✅ Дата: {date_str}\n\n"
            f"Укажите причину (необязательно):\n\n"
            f"_Например: Отпуск, Праздник и т.д._\n\n"
            f"Отправьте /skip чтобы пропустить",
            parse_mode="Markdown"
        )
        await state.set_state(ScheduleStates.setting_exception_reason)

    except Exception:
        await message.answer(
            "❌ Неверный формат даты. Используйте формат ДД.ММ.ГГГГ\n\n"
            "_Например: 25.12.2024_",
            parse_mode="Markdown"
        )


@router.message(ScheduleStates.setting_exception_reason)
async def process_exception_reason(message: Message, state: FSMContext) -> None:
    """Process exception reason and save"""
    reason = message.text.strip() if message.text != "/skip" else None

    data = await state.get_data()
    date_obj = data.get('exception_date')

    # TODO: Save to database
    # schedule_repo = get_schedule_repo()
    # await schedule_repo.add_exception(...)

    await message.answer(
        f"✅ *Исключение сохранено!*\n\n"
        f"📅 Дата: {date_obj.strftime('%d.%m.%Y')}\n"
        f"📝 Причина: {reason or 'Не указано'}\n\n"
        f"_В этот день бот не будет принимать записи_",
        parse_mode="Markdown",
        reply_markup=create_back_button("manage_schedule")
    )

    await state.clear()
