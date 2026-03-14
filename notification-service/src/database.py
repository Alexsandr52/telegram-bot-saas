"""
Notification Service - Database Connection
"""
import asyncpg
from loguru import logger
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from config import Settings, get_settings


class NotificationDatabase:
    """Database connection for notification service"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Create connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            logger.info("Database connection pool created")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise

    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")

    async def get_pending_notifications(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get pending notifications that should be sent now

        Args:
            limit: Maximum number of notifications to fetch

        Returns:
            List of notification rows with bot info
        """
        # Simplified approach - get all data in one query without locking
        query = """
            SELECT
                nq.*,
                b.bot_token,
                b.bot_username,
                c.telegram_id as client_telegram_id,
                c.first_name || ' ' || COALESCE(c.last_name, '') as client_name,
                m.telegram_id as master_telegram_id
            FROM notifications_queue nq
            JOIN bots b ON b.id = nq.bot_id
            LEFT JOIN clients c ON c.id = nq.client_id
            LEFT JOIN masters m ON m.id = nq.master_id
            WHERE nq.status = 'pending'
                AND nq.send_at <= NOW()
                AND nq.attempts < nq.max_attempts
            ORDER BY nq.send_at ASC
            LIMIT $1
        """

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, limit)
                logger.info(f"Retrieved {len(rows)} pending notifications")
                if rows:
                    logger.debug(f"First notification row: {dict(rows[0])}")
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting pending notifications: {e}")
            return []

    async def mark_notification_sent(self, notification_id: str):
        """Mark notification as sent"""
        query = """
            UPDATE notifications_queue
            SET status = 'sent',
                sent_at = NOW(),
                attempts = attempts + 1
            WHERE id = $1
        """

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(query, notification_id)
                logger.info(f"Notification {notification_id} marked as sent")
        except Exception as e:
            logger.error(f"Error marking notification as sent: {e}")

    async def mark_notification_failed(self, notification_id: str, error_message: str):
        """Mark notification as failed"""
        query = """
            UPDATE notifications_queue
            SET status = 'failed',
                error_message = $2,
                attempts = attempts + 1
            WHERE id = $1
        """

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(query, notification_id, error_message)
                logger.warning(f"Notification {notification_id} marked as failed: {error_message}")
        except Exception as e:
            logger.error(f"Error marking notification as failed: {e}")

    async def retry_failed_notifications(self, older_than_minutes: int = 5):
        """
        Retry failed notifications that are older than specified minutes

        Args:
            older_than_minutes: Minutes after which to retry
        """
        query = """
            UPDATE notifications_queue
            SET status = 'pending',
                error_message = NULL
            WHERE status = 'failed'
                AND attempts < max_attempts
                AND updated_at < NOW() - INTERVAL '1 minute' * $1
        """

        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(query, older_than_minutes)
                # Parse result to get count
                count = int(result.split()[-1])
                if count > 0:
                    logger.info(f"Retried {count} failed notifications")
        except Exception as e:
            logger.error(f"Error retrying failed notifications: {e}")

    async def cleanup_old_notifications(self, days: int = 7):
        """
        Delete old sent/failed notifications

        Args:
            days: Number of days to keep notifications
        """
        query = """
            DELETE FROM notifications_queue
            WHERE status IN ('sent', 'failed')
                AND created_at < NOW() - INTERVAL '1 day' * $1
        """

        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(query, days)
                count = int(result.split()[-1])
                if count > 0:
                    logger.info(f"Cleaned up {count} old notifications")
        except Exception as e:
            logger.error(f"Error cleaning up old notifications: {e}")

    async def schedule_reminder_24h(self, appointment_id: str, client_telegram_id: int,
                                  send_at: datetime, bot_id: str):
        """Schedule 24-hour reminder for appointment"""
        await self._schedule_reminder(
            appointment_id=appointment_id,
            client_telegram_id=client_telegram_id,
            send_at=send_at,
            bot_id=bot_id,
            reminder_type="reminder_24h"
        )

    async def schedule_reminder_2h(self, appointment_id: str, client_telegram_id: int,
                                 send_at: datetime, bot_id: str):
        """Schedule 2-hour reminder for appointment"""
        await self._schedule_reminder(
            appointment_id=appointment_id,
            client_telegram_id=client_telegram_id,
            send_at=send_at,
            bot_id=bot_id,
            reminder_type="reminder_2h"
        )

    async def _schedule_reminder(self, appointment_id: str, client_telegram_id: int,
                               send_at: datetime, bot_id: str, reminder_type: str):
        """Helper method to schedule reminder"""
        query = """
            INSERT INTO notifications_queue (bot_id, client_id, type, message, send_at, status, max_attempts)
            SELECT
                $1 as bot_id,
                c.id as client_id,
                $2 as type,
                $3 as message,
                $4 as send_at,
                'pending' as status,
                3 as max_attempts
            FROM appointments a
            JOIN clients c ON c.id = a.client_id
            WHERE a.id = $5 AND c.telegram_id = $6
        """

        message = self._get_reminder_message(reminder_type)

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    query,
                    bot_id,
                    reminder_type,
                    message,
                    send_at,
                    appointment_id,
                    client_telegram_id
                )
                logger.info(f"Scheduled {reminder_type} for appointment {appointment_id}")
        except Exception as e:
            logger.error(f"Error scheduling reminder: {e}")

    def _get_reminder_message(self, reminder_type: str) -> str:
        """Get reminder message based on type"""
        if reminder_type == "reminder_24h":
            return "📅 *Напоминание о записи*\n\nЗдравствуйте! Напоминаем, что у вас завтра запись. Ждем вас в назначенное время!"
        elif reminder_type == "reminder_2h":
            return "⏰ *Напоминание о записи*\n\nЗдравствуйте! Напоминаем, что ваша запись через 2 часа. Пожалуйста, будьте вовремя!"
        else:
            return "У вас запланирована запись!"


# Global database instance
_db: Optional[NotificationDatabase] = None


def init_database(database_url: str) -> NotificationDatabase:
    """Initialize database connection"""
    global _db
    _db = NotificationDatabase(database_url)
    return _db


def get_database() -> Optional[NotificationDatabase]:
    """Get database instance"""
    return _db