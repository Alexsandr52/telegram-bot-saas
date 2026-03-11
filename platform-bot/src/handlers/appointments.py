"""
Appointments Handler for Platform Bot
Shows and manages client appointments for masters
"""
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger

from src.utils.repositories import get_bot_repo, get_appointment_repo
from src.keyboards import (
    create_back_button,
    get_bot_actions_keyboard
)


router = Router(name="appointments_handler")


# ============================================
# Appointments List
# ============================================

@router.callback_query(F.data.startswith("bot_appointments:"))
async def show_appointments(callback: CallbackQuery) -> None:
    """Show appointments for a bot"""
    bot_repo = get_bot_repo()
    bot_id = callback.data.split(":")[1]

    try:
        # Verify bot
        bot = await bot_repo.get_bot_by_id(bot_id)
        if not bot:
            await callback.answer("❌ Бот не найден", show_alert=True)
            return

        # Get appointments
        appointment_repo = get_appointment_repo()
        appointments = await appointment_repo.get_bot_appointments(bot_id, limit=20)

        if not appointments:
            text = (
                "📋 *Записи клиентов*\n\n"
                "Пока нет записей."
            )
        else:
            text = "📋 *Записи клиентов*\n\n"

            for appt in appointments[:10]:  # Show first 10
                start_time = appt['start_time']
                client_name = f"{appt.get('first_name', '')} {appt.get('last_name', '')}".strip() or "Клиент"
                service = appt.get('service_name', 'Услуга')

                # Status emoji
                status_emoji = {
                    'pending': '⏳',
                    'confirmed': '✅',
                    'completed': '✅',
                    'cancelled': '❌'
                }.get(appt['status'], '❓')

                text += (
                    f"{status_emoji} *{client_name}*\n"
                    f"📅 {start_time.strftime('%d.%m.%Y %H:%M')}\n"
                    f"🔹 {service} - {appt['price']}₽\n\n"
                )

            if len(appointments) > 10:
                text += f"_и ещё {len(appointments) - 10} записей..._"

        # Add statistics
        stats = await appointment_repo.get_bot_statistics(bot_id)
        text += (
            f"\n\n📊 *Статистика:*\n"
            f"Всего записей: {stats['total_appointments']}\n"
            f"Выручка: {stats['total_revenue']:.0f}₽\n"
            f"Клиентов: {stats['unique_clients']}\n"
        )

        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=create_back_button(f"bot_menu:{bot_id}")
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error showing appointments: {e}")
        await callback.answer("❌ Ошибка при загрузке записей", show_alert=True)


# ============================================
# Statistics
# ============================================

@router.callback_query(F.data.startswith("bot_statistics:"))
async def show_statistics(callback: CallbackQuery, bot_repo) -> None:
    """Show detailed statistics for a bot"""
    bot_id = callback.data.split(":")[1]

    try:
        # Verify bot
        bot = await bot_repo.get_bot_by_id(bot_id)
        if not bot:
            await callback.answer("❌ Бот не найден", show_alert=True)
            return

        # Get statistics
        appointment_repo = get_appointment_repo()
        stats = await appointment_repo.get_bot_statistics(bot_id)

        # Get appointments for current month
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_appointments = await appointment_repo.get_appointments_by_date(
            bot_id, month_start, month_start + timedelta(days=32)
        )

        # Calculate month revenue
        month_revenue = sum(
            a['price'] for a in month_appointments if a['status'] != 'cancelled'
        )

        text = (
            f"📊 *Статистика*\n\n"
            f"📈 *Всего записей:* {stats['total_appointments']}\n"
            f"💰 *Общая выручка:* {stats['total_revenue']:.0f}₽\n"
            f"👥 *Уникальных клиентов:* {stats['unique_clients']}\n\n"
            f"📅 *Этот месяц:*\n"
            f"Записей: {len(month_appointments)}\n"
            f"Выручка: {month_revenue:.0f}₽\n\n"
        )

        # Status breakdown
        if stats['status_breakdown']:
            text += "*Статусы записей:*\n"
            for status, count in stats['status_breakdown'].items():
                status_emoji = {
                    'pending': '⏳',
                    'confirmed': '✅',
                    'completed': '✅',
                    'cancelled': '❌'
                }.get(status, '❓')

                status_name = {
                    'pending': 'Ожидают',
                    'confirmed': 'Подтверждены',
                    'completed': 'Выполнены',
                    'cancelled': 'Отменены'
                }.get(status, status)

                text += f"{status_emoji} {status_name}: {count}\n"

        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=create_back_button(f"bot_menu:{bot_id}")
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error showing statistics: {e}")
        await callback.answer("❌ Ошибка при загрузке статистики", show_alert=True)
