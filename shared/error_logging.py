"""
Error Logging System
Centralized error logging to database with notification support
"""
import asyncio
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from loguru import logger
import asyncpg


class ErrorLevel(Enum):
    """Error severity levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ErrorCategory(Enum):
    """Error categories for better organization"""
    DATABASE = "database"
    NETWORK = "network"
    TELEGRAM_API = "telegram_api"
    WEBHOOK = "webhook"
    AUTHENTICATION = "authentication"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    EXTERNAL_API = "external_api"


class ErrorLogger:
    """
    Centralized error logging to database
    Logs errors separately from application logs
    """

    def __init__(self, dsn: str, min_pool_size: int = 2, max_pool_size: int = 5):
        """
        Initialize error logger with database connection pool

        Args:
            dsn: PostgreSQL connection string
            min_pool_size: Minimum pool size (keep low as this is for errors only)
            max_pool_size: Maximum pool size
        """
        self.dsn = dsn
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """Create connection pool"""
        if self._pool is None:
            try:
                self._pool = await asyncpg.create_pool(
                    self.dsn,
                    min_size=self.min_pool_size,
                    max_size=self.max_pool_size,
                    command_timeout=30
                )
                logger.info("Error logger database pool created")
            except Exception as e:
                logger.error(f"Failed to create error logger pool: {e}")
                # Fail gracefully - don't crash the app
                self._pool = None

    async def close(self) -> None:
        """Close connection pool"""
        if self._pool:
            await self._pool.close()
            logger.info("Error logger database pool closed")
            self._pool = None

    async def log_error(
        self,
        level: ErrorLevel,
        category: ErrorCategory,
        error_message: str,
        error_type: str,
        stack_trace: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        bot_id: Optional[str] = None,
        service_name: Optional[str] = None
    ) -> bool:
        """
        Log error to database with retry logic

        Args:
            level: Error severity level
            category: Error category
            error_message: Error message
            error_type: Type of error (e.g., exception class name)
            stack_trace: Full stack trace if available
            context: Additional context data
            user_id: Telegram user ID if applicable
            bot_id: Bot UUID if applicable
            service_name: Service name (web-api, platform-bot, etc.)

        Returns:
            True if logged successfully, False otherwise
        """
        if not self._pool:
            return False

        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO error_logs (
                        level, category, error_message, error_type,
                        stack_trace, context, user_id, bot_id, service_name,
                        created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                    """,
                    level.value,
                    category.value,
                    error_message[:2000],  # Limit message length
                    error_type[:100],  # Limit type length
                    stack_trace,
                    context,
                    user_id,
                    bot_id,
                    service_name
                )

            logger.info(f"Error logged: {category.value} - {error_type}")

            # Check if we need to send notification
            if level in [ErrorLevel.ERROR, ErrorLevel.CRITICAL]:
                await self._check_and_notify(level, category, error_message, context)

            return True

        except Exception as e:
            # Don't let error logging crash the app
            logger.error(f"Failed to log error to database: {e}")
            logger.error(f"Original error: {error_message}")
            return False

    async def log_exception(
        self,
        exception: Exception,
        level: ErrorLevel = ErrorLevel.ERROR,
        category: Optional[ErrorCategory] = None,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        bot_id: Optional[str] = None,
        service_name: Optional[str] = None
    ) -> bool:
        """
        Log exception with full stack trace

        Args:
            exception: The exception to log
            level: Error level
            category: Error category
            context: Additional context
            user_id: Telegram user ID if applicable
            bot_id: Bot UUID if applicable
            service_name: Service name

        Returns:
            True if logged successfully, False otherwise
        """
        import traceback

        error_type = type(exception).__name__
        error_message = str(exception)
        stack_trace = traceback.format_exc()

        if category is None:
            # Auto-detect category based on exception type
            category = self._detect_error_category(exception)

        return await self.log_error(
            level=level,
            category=category,
            error_message=error_message,
            error_type=error_type,
            stack_trace=stack_trace,
            context=context,
            user_id=user_id,
            bot_id=bot_id,
            service_name=service_name
        )

    def _detect_error_category(self, exception: Exception) -> ErrorCategory:
        """
        Auto-detect error category based on exception type

        Args:
            exception: The exception

        Returns:
            Detected error category
        """
        import asyncpg
        import httpx

        exception_type = type(exception).__name__
        module_name = type(exception).__module__ or ""

        if "asyncpg" in module_name or "postgres" in str(exception).lower():
            return ErrorCategory.DATABASE
        elif "httpx" in module_name or "aiohttp" in module_name:
            return ErrorCategory.NETWORK
        elif "telegram" in str(exception).lower():
            return ErrorCategory.TELEGRAM_API
        elif "webhook" in str(exception).lower():
            return ErrorCategory.WEBHOOK
        elif "auth" in str(exception).lower() or "token" in str(exception).lower():
            return ErrorCategory.AUTHENTICATION
        else:
            return ErrorCategory.BUSINESS_LOGIC

    async def _check_and_notify(
        self,
        level: ErrorLevel,
        category: ErrorCategory,
        error_message: str,
        context: Optional[Dict[str, Any]]
    ) -> None:
        """
        Check if notification should be sent based on error frequency and type

        Args:
            level: Error level
            category: Error category
            error_message: Error message
            context: Additional context
        """
        try:
            # Only send notifications for CRITICAL errors or specific ERROR types
            if level != ErrorLevel.CRITICAL:
                # Check if this is a frequently occurring error that shouldn't notify
                if not await self._should_notify(category, error_message):
                    return

            # Get admin Telegram ID from environment
            admin_id = self._get_admin_id()
            if not admin_id:
                return

            # Format notification message
            message = self._format_notification(level, category, error_message, context)

            # Send notification via Telegram
            await self._send_telegram_notification(admin_id, message)

        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")

    async def _should_notify(self, category: ErrorCategory, error_message: str) -> bool:
        """
        Check if error should trigger notification based on frequency

        Args:
            category: Error category
            error_message: Error message

        Returns:
            True if notification should be sent
        """
        try:
            # Check if we've seen this error recently (last 5 minutes)
            async with self._pool.acquire() as conn:
                count = await conn.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM error_logs
                    WHERE category = $1
                      AND error_message = $2
                      AND created_at > NOW() - INTERVAL '5 minutes'
                    """,
                    category.value,
                    error_message[:200]
                )

                # Only notify if this is a new error (not seen in last 5 minutes)
                return count == 0

        except Exception:
            # If we can't check frequency, err on the side of notifying
            return True

    def _get_admin_id(self) -> Optional[int]:
        """
        Get admin Telegram ID from environment

        Returns:
            Admin Telegram ID or None
        """
        import os
        admin_id = os.getenv("ADMIN_TELEGRAM_ID")
        if admin_id:
            try:
                return int(admin_id)
            except ValueError:
                return None
        return None

    def _format_notification(
        self,
        level: ErrorLevel,
        category: ErrorCategory,
        error_message: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """
        Format error notification message

        Args:
            level: Error level
            category: Error category
            error_message: Error message
            context: Additional context

        Returns:
            Formatted notification message
        """
        level_emoji = {
            ErrorLevel.ERROR: "⚠️",
            ErrorLevel.CRITICAL: "🚨"
        }.get(level, "ℹ️")

        category_emoji = {
            ErrorCategory.DATABASE: "🗄️",
            ErrorCategory.NETWORK: "🌐",
            ErrorCategory.TELEGRAM_API: "🤖",
            ErrorCategory.WEBHOOK: "🔗",
            ErrorCategory.AUTHENTICATION: "🔑",
            ErrorCategory.BUSINESS_LOGIC: "💼",
            ErrorCategory.SYSTEM: "⚙️"
        }.get(category, "❓")

        message = f"{level_emoji} {category_emoji} *{level.value}* Error\n\n"
        message += f"**Category:** {category.value}\n"
        message += f"**Message:** {error_message[:200]}\n\n"

        if context:
            message += "**Context:**\n"
            for key, value in list(context.items())[:5]:  # Limit context items
                message += f"• {key}: {str(value)[:100]}\n"

        return message

    async def _send_telegram_notification(self, chat_id: int, message: str) -> bool:
        """
        Send notification via Telegram Bot API

        Args:
            chat_id: Telegram chat ID
            message: Message to send

        Returns:
            True if sent successfully
        """
        import os
        admin_bot_token = os.getenv("ADMIN_BOT_TOKEN")

        if not admin_bot_token:
            return False

        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{admin_bot_token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": message,
                        "parse_mode": "Markdown"
                    }
                )

                if response.status_code == 200:
                    logger.info(f"Error notification sent to admin: {chat_id}")
                    return True
                else:
                    logger.error(f"Failed to send notification: {response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")
            return False

    async def get_recent_errors(
        self,
        hours: int = 24,
        level: Optional[ErrorLevel] = None,
        limit: int = 100
    ) -> list[dict]:
        """
        Get recent errors from database

        Args:
            hours: Number of hours to look back
            level: Filter by error level (optional)
            limit: Maximum number of errors to return

        Returns:
            List of error dictionaries
        """
        if not self._pool:
            return []

        try:
            async with self._pool.acquire() as conn:
                query = """
                    SELECT id, level, category, error_message, error_type,
                           stack_trace, context, user_id, bot_id, service_name,
                           created_at
                    FROM error_logs
                    WHERE created_at > NOW() - INTERVAL $1 hours
                """
                params = [hours]
                param_count = 2

                if level:
                    query += " AND level = $" + str(param_count) + ""
                    params.append(level.value)
                    param_count += 1

                query += " ORDER BY created_at DESC LIMIT $" + str(param_count) + ""
                params.append(limit)

                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error fetching recent errors: {e}")
            return []

    async def get_error_statistics(
        self,
        days: int = 7
    ) -> dict:
        """
        Get error statistics for monitoring

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with error statistics
        """
        if not self._pool:
            return {}

        try:
            async with self._pool.acquire() as conn:
                # Total errors
                total_errors = await conn.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM error_logs
                    WHERE created_at > NOW() - INTERVAL $1 days
                    """,
                    days
                )

                # Errors by level
                errors_by_level = await conn.fetch(
                    """
                    SELECT level, COUNT(*) as count
                    FROM error_logs
                    WHERE created_at > NOW() - INTERVAL $1 days
                    GROUP BY level
                    """,
                    days
                )

                # Errors by category
                errors_by_category = await conn.fetch(
                    """
                    SELECT category, COUNT(*) as count
                    FROM error_logs
                    WHERE created_at > NOW() - INTERVAL $1 days
                    GROUP BY category
                    """,
                    days
                )

                # Critical errors
                critical_errors = await conn.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM error_logs
                    WHERE level = 'CRITICAL'
                      AND created_at > NOW() - INTERVAL $1 days
                    """,
                    days
                )

                return {
                    "total_errors": total_errors or 0,
                    "critical_errors": critical_errors or 0,
                    "by_level": {row['level']: row['count'] for row in errors_by_level},
                    "by_category": {row['category']: row['count'] for row in errors_by_category},
                    "period_days": days
                }

        except Exception as e:
            logger.error(f"Error fetching statistics: {e}")
            return {}


# Global error logger instance
_error_logger: Optional[ErrorLogger] = None


def get_error_logger() -> Optional[ErrorLogger]:
    """Get global error logger instance"""
    return _error_logger


async def init_error_logging(dsn: str) -> ErrorLogger:
    """
    Initialize global error logger

    Args:
        dsn: Database connection string

    Returns:
        ErrorLogger instance
    """
    global _error_logger
    if _error_logger is None:
        _error_logger = ErrorLogger(dsn)
        await _error_logger.connect()
        logger.info("Error logging system initialized")
    return _error_logger


async def close_error_logging() -> None:
    """Close global error logger"""
    global _error_logger
    if _error_logger:
        await _error_logger.close()
        _error_logger = None
        logger.info("Error logging system closed")


# Convenience functions for logging

async def log_error(
    level: ErrorLevel,
    category: ErrorCategory,
    error_message: str,
    error_type: str,
    stack_trace: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None,
    bot_id: Optional[str] = None,
    service_name: Optional[str] = None
) -> bool:
    """
    Log error to database

    Returns:
        True if logged successfully
    """
    logger_instance = get_error_logger()
    if logger_instance:
        return await logger_instance.log_error(
            level=level,
            category=category,
            error_message=error_message,
            error_type=error_type,
            stack_trace=stack_trace,
            context=context,
            user_id=user_id,
            bot_id=bot_id,
            service_name=service_name
        )
    return False


async def log_exception(
    exception: Exception,
    level: ErrorLevel = ErrorLevel.ERROR,
    category: Optional[ErrorCategory] = None,
    context: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None,
    bot_id: Optional[str] = None,
    service_name: Optional[str] = None
) -> bool:
    """
    Log exception with full stack trace

    Returns:
        True if logged successfully
    """
    logger_instance = get_error_logger()
    if logger_instance:
        return await logger_instance.log_exception(
            exception=exception,
            level=level,
            category=category,
            context=context,
            user_id=user_id,
            bot_id=bot_id,
            service_name=service_name
        )
    return False


def with_error_logging(
    category: ErrorCategory,
    service_name: Optional[str] = None
):
    """
    Decorator for automatic error logging

    Args:
        category: Error category
        service_name: Service name

    Returns:
        Decorator function
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                await log_exception(
                    exception=e,
                    category=category,
                    service_name=service_name,
                    context={
                        'function': func.__name__,
                        'module': func.__module__
                    }
                )
                raise  # Re-raise exception
        return wrapper
    return decorator
