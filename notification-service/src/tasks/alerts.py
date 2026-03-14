"""
Notification Tasks - Alerts for Masters
"""
import httpx
from datetime import datetime
from loguru import logger
from typing import Optional

from models import Notification, NotificationType, TelegramMessage


class AlertSender:
    """Send alert notifications to masters"""

    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=10.0)

    async def send_alert(self, notification: Notification) -> bool:
        """
        Send alert to master

        Args:
            notification: Notification to send

        Returns:
            True if sent successfully, False otherwise
        """
        # Prepare message based on type
        message = self._prepare_alert_message(notification)

        # Send via Telegram API
        try:
            url = f"https://api.telegram.org/bot{notification.bot_token}/sendMessage"

            response = await self.http_client.post(
                url,
                json={
                    "chat_id": notification.master_telegram_id,
                    "text": message,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True
                }
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    logger.info(f"✅ Alert sent to master {notification.master_telegram_id} "
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
            logger.error(f"❌ Error sending alert: {e}")
            return False

    def _prepare_alert_message(self, notification: Notification) -> str:
        """
        Prepare alert message based on type

        Args:
            notification: Notification to prepare message for

        Returns:
            Formatted message text
        """
        if notification.type == NotificationType.NEW_BOOKING:
            return self._format_new_booking_alert(notification)
        elif notification.type == NotificationType.CANCELLED_BOOKING:
            return self._format_cancelled_booking_alert(notification)
        else:
            return notification.message

    def _format_new_booking_alert(self, notification: Notification) -> str:
        """Format new booking alert message"""
        metadata = notification.metadata or {}

        service_name = metadata.get('service_name', 'услуга')
        appointment_time = metadata.get('appointment_time')
        client_name = notification.client_name
        client_telegram_id = notification.client_telegram_id

        message = (
            f"🔔 *Новая запись!*\n\n"
            f"🎉 *Услуга:* {service_name}\n"
            f"👤 *Клиент:* {client_name}\n"
        )

        if appointment_time:
            try:
                appt_time = datetime.fromisoformat(appointment_time) if isinstance(appointment_time, str) else appointment_time
                day_names = ['Понедельник', 'Вторник', 'Среду', 'Четверг', 'Пятницу', 'Субботу', 'Воскресенье']
                weekday = day_names[appt_time.weekday()]
                date_str = appt_time.strftime('%d.%m.%Y')
                time_str = appt_time.strftime('%H:%M')

                message += f"📅 *Дата:* {date_str} ({weekday})\n"
                message += f"🕐 *Время:* {time_str}\n"
            except Exception as e:
                logger.error(f"Error parsing appointment time: {e}")

        # Add contact info
        contact_info = []
        if client_telegram_id:
            contact_info.append(f"📱 [Связаться с клиентом](tg://user?id={client_telegram_id})")

        if contact_info:
            message += "\n" + "\n".join(contact_info) + "\n"

        message += f"\nID записи: {notification.id[:8]}..."

        return message

    def _format_cancelled_booking_alert(self, notification: Notification) -> str:
        """Format cancelled booking alert message"""
        metadata = notification.metadata or {}

        service_name = metadata.get('service_name', 'услуга')
        appointment_time = metadata.get('appointment_time')
        client_name = notification.client_name

        message = (
            f"❌ *Запись отменена!*\n\n"
            f"🎉 *Услуга:* {service_name}\n"
            f"👤 *Клиент:* {client_name}\n"
        )

        if appointment_time:
            try:
                appt_time = datetime.fromisoformat(appointment_time) if isinstance(appointment_time, str) else appointment_time
                day_names = ['Понедельник', 'Вторник', 'Среду', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
                weekday = day_names[appt_time.weekday()]
                date_str = appt_time.strftime('%d.%m.%Y')
                time_str = appt_time.strftime('%H:%M')

                message += f"📅 *Дата:* {date_str} ({weekday})\n"
                message += f"🕐 *Время:* {time_str}\n"
            except Exception as e:
                logger.error(f"Error parsing appointment time: {e}")

        message += f"\n📝 ID записи: {notification.id[:8]}..."

        return message

    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()
        logger.info("Alert sender closed")