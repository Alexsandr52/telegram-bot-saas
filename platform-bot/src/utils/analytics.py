"""
Analytics utilities for Platform Bot
Log user actions and events for statistics
"""
from typing import Optional, Dict, Any
from loguru import logger
from datetime import datetime
import uuid

from .db import Database


class PlatformAnalytics:
    """Analytics for platform-level events"""

    def __init__(self, db: Database):
        self.db = db

    async def log_event(
        self,
        event_type: str,
        master_id: Optional[uuid.UUID] = None,
        user_id: Optional[int] = None,
        event_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log analytics event

        Args:
            event_type: Type of event (bot_started, bot_created, etc.)
            master_id: Master UUID (optional)
            user_id: Telegram user ID (optional)
            event_data: Additional event data as dict
        """
        try:
            await self.db.execute(
                """
                INSERT INTO analytics_events (bot_id, event_type, user_id, event_data)
                VALUES ($1, $2, $3, $4)
                """,
                None,  # bot_id is NULL for platform events
                event_type,
                user_id,
                event_data or {}
            )
            logger.debug(f"Analytics event logged: {event_type}")
        except Exception as e:
            logger.error(f"Error logging analytics event: {e}")


async def log_platform_event(
    event_type: str,
    master_id: Optional[uuid.UUID] = None,
    user_id: Optional[int] = None,
    event_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Convenience function to log platform-level analytics events

    Args:
        event_type: Type of event
        master_id: Master UUID (optional)
        user_id: Telegram user ID (optional)
        event_data: Additional event data
    """
    from .repositories import get_db

    db = get_db()
    analytics = PlatformAnalytics(db)
    await analytics.log_event(event_type, master_id, user_id, event_data)


# Event types
class PlatformEventType:
    """Platform-level event types"""
    BOT_STARTED = "bot_started"
    BOT_CREATED = "bot_created"
    BOT_RESTARTED = "bot_restarted"
    BOT_STOPPED = "bot_stopped"
    SERVICE_CREATED = "service_created"
    SERVICE_UPDATED = "service_updated"
    SERVICE_DELETED = "service_deleted"
    SUBSCRIPTION_VIEWED = "subscription_viewed"
    WEB_PANEL_OPENED = "web_panel_opened"
    SETTINGS_VIEWED = "settings_viewed"
    STATISTICS_VIEWED = "statistics_viewed"
