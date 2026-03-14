"""
Notification Tasks - Reminders for Clients
"""
import httpx
from datetime import datetime, timedelta
from loguru import logger
from typing import Optional

from models import Notification, NotificationType, TelegramMessage
from database import NotificationDatabase


class ReminderScheduler:
    """Schedule and manage reminders for appointments"""

    def __init__(self, db: NotificationDatabase):
        self.db = db

    async def schedule_appointment_reminders(self, appointment_id: str, bot_id: str,
                                         client_telegram_id: int, appointment_time: datetime):
        """
        Schedule all reminders for an appointment

        Args:
            appointment_id: Appointment UUID
            bot_id: Bot UUID
            client_telegram_id: Client's Telegram ID
            appointment_time: Appointment start time
        """
        # Schedule 24-hour reminder
        reminder_24h_time = appointment_time - timedelta(hours=24)
        if reminder_24h_time > datetime.now(reminder_24h_time.tzinfo):
            await self.db.schedule_reminder_24h(
                appointment_id=appointment_id,
                client_telegram_id=client_telegram_id,
                send_at=reminder_24h_time,
                bot_id=bot_id
            )
            logger.info(f"Scheduled 24h reminder for appointment {appointment_id}")

        # Schedule 2-hour reminder
        reminder_2h_time = appointment_time - timedelta(hours=2)
        if reminder_2h_time > datetime.now(reminder_2h_time.tzinfo):
            await self.db.schedule_reminder_2h(
                appointment_id=appointment_id,
                client_telegram_id=client_telegram_id,
                send_at=reminder_2h_time,
                bot_id=bot_id
            )
            logger.info(f"Scheduled 2h reminder for appointment {appointment_id}")

    async def cancel_appointment_reminders(self, appointment_id: str):
        """
        Cancel all reminders for a cancelled appointment

        Args:
            appointment_id: Appointment UUID
        """
        query = """
            UPDATE notifications_queue
            SET status = 'failed',
                error_message = 'Appointment cancelled'
            WHERE type IN ('reminder_24h', 'reminder_2h')
                AND metadata->>'appointment_id' = $1
                AND status = 'pending'
        """

        try:
            async with self.db.pool.acquire() as conn:
                result = await conn.execute(query, appointment_id)
                count = int(result.split()[-1])
                if count > 0:
                    logger.info(f"Cancelled {count} reminders for appointment {appointment_id}")
        except Exception as e:
            logger.error(f"Error cancelling reminders: {e}")


class ReminderSender:
    """Send reminder notifications to clients"""

    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=10.0)

    async def send_reminder(self, notification: Notification) -> bool:
        """
        Send reminder to client

        Args:
            notification: Notification to send

        Returns:
            True if sent successfully, False otherwise
        """
        # Prepare message
        message = self._prepare_reminder_message(notification)

        # Send via Telegram API
        try:
            url = f"https://api.telegram.org/bot{notification.bot_token}/sendMessage"

            response = await self.http_client.post(
                url,
                json={
                    "chat_id": notification.client_telegram_id,
                    "text": message,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True
                }
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    logger.info(f"✅ Reminder sent to client {notification.client_telegram_id} "
                              f"(notification: {notification.id})")
                    return True
                else:
                    error = result.get("description", "Unknown error")
                    logger.error(f"❌ Telegram API error: {error}")
                    return False
            else:
                logger.error(f"❌ HTTP error: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"❌ Error sending reminder: {e}")
            return False

    def _prepare_reminder_message(self, notification: Notification) -> str:
        """
        Prepare reminder message based on type

        Args:
            notification: Notification to prepare message for

        Returns:
            Formatted message text
        """
        if notification.type == NotificationType.REMINDER_24H:
            return self._format_24h_reminder(notification)
        elif notification.type == NotificationType.REMINDER_2H:
            return self._format_2h_reminder(notification)
        else:
            return notification.message

    def _format_24h_reminder(self, notification: Notification) -> str:
        """Format 24-hour reminder message"""
        metadata = notification.metadata or {}

        appointment_time = metadata.get('appointment_time')
        service_name = metadata.get('service_name', 'услуга')
        bot_name = notification.bot_username

        message = (
            f"📅 *Напоминание о записи (через 24 часа)*\n\n"
            f"Добрый день, {notification.client_name}! 👋\n\n"
            f"Напоминаем, что завтра у вас запись:\n"
            f"🎉 *Услуга:* {service_name}\n"
        )

        if appointment_time:
            try:
                appt_time = datetime.fromisoformat(appointment_time) if isinstance(appointment_time, str) else appointment_time
                day_names = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
                weekday = day_names[appt_time.weekday()]
                date_str = appt_time.strftime('%d.%m.%Y')
                time_str = appt_time.strftime('%H:%M')

                message += f"📅 *Дата:* {date_str} ({weekday})\n"
                message += f"🕐 *Время:* {time_str}\n"
            except Exception as e:
                logger.error(f"Error parsing appointment time: {e}")

        message += (
            f"\n💡 Пожалуйста, будьте вовремя!\n"
            f"Если вы не можете прийти, пожалуйста, отмените запись заранее.\n\n"
            f"С уважением, команда @{bot_name}"
        )

        return message

    def _format_2h_reminder(self, notification: Notification) -> str:
        """Format 2-hour reminder message"""
        metadata = notification.metadata or {}

        appointment_time = metadata.get('appointment_time')
        service_name = metadata.get('service_name', 'услуга')
        bot_name = notification.bot_username

        message = (
            f"⏰ *Напоминание о записи (через 2 часа)*\n\n"
            f"Добрый день, {notification.client_name}! 👋\n\n"
            f"Напоминаем, что через 2 часа у вас запись:\n"
            f"🎉 *Услуга:* {service_name}\n"
        )

        if appointment_time:
            try:
                appt_time = datetime.fromisoformat(appointment_time) if isinstance(appointment_time, str) else appointment_time
                time_str = appt_time.strftime('%H:%M')

                message += f"🕐 *Время:* {time_str}\n"
            except Exception as e:
                logger.error(f"Error parsing appointment time: {e}")

        message += (
            f"\n💡 Не забудьте быть вовремя!\n"
            f"С уважением, команда @{bot_name}"
        )

        return message

    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()
        logger.info("Reminder sender closed")