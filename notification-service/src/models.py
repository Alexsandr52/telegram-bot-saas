"""
Notification Service - Data Models
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class NotificationType(Enum):
    """Notification types"""
    REMINDER_24H = "reminder_24h"
    REMINDER_2H = "reminder_2h"
    NEW_BOOKING = "new_booking"
    CANCELLED_BOOKING = "cancelled_booking"
    CUSTOM = "custom"


class NotificationStatus(Enum):
    """Notification statuses"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


@dataclass
class Notification:
    """Notification data model"""
    id: str
    bot_id: str
    bot_token: str
    bot_username: str
    client_id: Optional[str]
    client_telegram_id: int
    client_name: str
    master_id: Optional[str]
    master_telegram_id: Optional[int]
    type: NotificationType
    message: str
    send_at: datetime
    status: NotificationStatus
    attempts: int = 0
    max_attempts: int = 3
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

    @classmethod
    def from_db_row(cls, row: Dict[str, Any], bot_token: str, bot_username: str) -> "Notification":
        """Create notification from database row"""
        # Debug logging
        from loguru import logger
        logger.debug(f"from_db_row received row type: {type(row)}, value: {row}")

        # Handle different row types
        if isinstance(row, str):
            logger.error(f"Received string instead of dict: {row}")
            raise ValueError(f"Expected dict, got string: {row}")

        # Convert Record to dict if needed
        if hasattr(row, '_asdict'):
            row = row._asdict()
        elif hasattr(row, 'keys'):
            row = dict(row)

        logger.debug(f"Row after conversion: {row}")

        return cls(
            id=str(row.get('id', '')),
            bot_id=str(row.get('bot_id', '')),
            bot_token=bot_token,
            bot_username=bot_username,
            client_id=str(row.get('client_id')) if row.get('client_id') else None,
            client_telegram_id=row.get('client_telegram_id', 0),
            client_name=row.get('client_name', 'Клиент'),
            master_id=str(row.get('master_id')) if row.get('master_id') else None,
            master_telegram_id=row.get('master_telegram_id'),
            type=NotificationType(row.get('type', 'custom')),
            message=row.get('message', ''),
            send_at=row.get('send_at'),
            status=NotificationStatus(row.get('status', 'pending')),
            attempts=row.get('attempts', 0),
            max_attempts=row.get('max_attempts', 3),
            error_message=row.get('error_message'),
            metadata=row.get('metadata', {})
        )


@dataclass
class TelegramMessage:
    """Telegram message data"""
    chat_id: int
    text: str
    parse_mode: str = "Markdown"
    disable_web_page_preview: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API call"""
        return {
            "chat_id": self.chat_id,
            "text": self.text,
            "parse_mode": self.parse_mode,
            "disable_web_page_preview": self.disable_web_page_preview
        }