"""
Shared Logging Configuration
Centralized logging system for all services
"""
import sys
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from enum import Enum


class LogLevel(str, Enum):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(str, Enum):
    """Log formats"""
    TEXT = "text"
    JSON = "json"
    STRUCTURED = "structured"


class LoggerConfig:
    """Centralized logger configuration"""

    def __init__(
        self,
        service_name: str,
        level: LogLevel = LogLevel.INFO,
        log_format: LogFormat = LogFormat.JSON,
        log_file: Optional[str] = None,
        console_output: bool = True,
        log_to_db: bool = False,
        sentry_dsn: Optional[str] = None
    ):
        self.service_name = service_name
        self.level = level
        self.log_format = log_format
        self.log_file = log_file
        self.console_output = console_output
        self.log_to_db = log_to_db
        self.sentry_dsn = sentry_dsn

    def get_logger(self) -> 'StructuredLogger':
        """Get configured logger instance"""
        return StructuredLogger(
            service_name=self.service_name,
            level=self.level,
            log_format=self.log_format,
            log_file=self.log_file,
            console_output=self.console_output,
            log_to_db=self.log_to_db,
            sentry_dsn=self.sentry_dsn
        )


class StructuredLogger:
    """
    Structured logger with JSON output, rotation, and database integration
    """

    def __init__(
        self,
        service_name: str,
        level: LogLevel = LogLevel.INFO,
        log_format: LogFormat = LogFormat.JSON,
        log_file: Optional[str] = None,
        console_output: bool = True,
        log_to_db: bool = False,
        sentry_dsn: Optional[str] = None
    ):
        self.service_name = service_name
        self.level = level
        self.log_format = log_format
        self.log_file = log_file
        self.console_output = console_output
        self.log_to_db = log_to_db
        self.sentry_dsn = sentry_dsn

        # Setup log file directory
        self._setup_log_file()

        # Configure standard logger
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(getattr(logging, level.value))

        # Setup handlers
        self._setup_handlers()

        # Setup Sentry if DSN provided
        if sentry_dsn:
            self._setup_sentry()

    def _setup_log_file(self):
        """Setup log file directory"""
        if self.log_file:
            log_path = Path(self.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

    def _setup_handlers(self):
        """Setup log handlers"""
        handlers = []

        # Console handler
        if self.console_output:
            console_handler = self._get_console_handler()
            handlers.append(console_handler)

        # File handler with rotation
        if self.log_file:
            file_handler = self._get_file_handler()
            handlers.append(file_handler)

        # Database handler (for centralized logging)
        if self.log_to_db:
            db_handler = DatabaseLogHandler()
            handlers.append(db_handler)

        # Add all handlers
        for handler in handlers:
            self.logger.addHandler(handler)

    def _get_console_handler(self) -> logging.Handler:
        """Get console handler based on format"""
        if self.log_format == LogFormat.JSON:
            return logging.StreamHandler(sys.stdout)

        handler = logging.StreamHandler(sys.stdout)
        if self.log_format == LogFormat.TEXT:
            handler.setFormatter(logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s - %(message)s'
            ))
        elif self.log_format == LogFormat.STRUCTURED:
            handler.setFormatter(logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s'
            ))
        return handler

    def _get_file_handler(self) -> logging.Handler:
        """Get file handler with rotation"""
        from logging.handlers import RotatingFileHandler

        # 10 MB per file, keep 5 files
        handler = RotatingFileHandler(
            self.log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )

        if self.log_format == LogFormat.JSON:
            handler.setFormatter(JsonFormatter(self.service_name))
        elif self.log_format == LogFormat.TEXT:
            handler.setFormatter(logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s - %(message)s'
            ))
        elif self.log_format == LogFormat.STRUCTURED:
            handler.setFormatter(logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s'
            ))

        return handler

    def _setup_sentry(self):
        """Setup Sentry integration for error tracking"""
        try:
            import sentry_sdk
            from sentry_sdk.integrations.logging import LoggingHandler, LoggingLevels

            sentry_sdk.init(
                dsn=self.sentry_dsn,
                traces_sample_rate=1.0,
                profiles_sample_rate=1.0,
                environment="production" if self.log_file else "development",
                release=getattr(__import__('__main__'), '__version__', '1.0.0')
            )

            # Add Sentry handler
            sentry_handler = LoggingHandler(
                level=LoggingLevels.ERROR
            )
            self.logger.addHandler(sentry_handler)

        except ImportError:
            # Sentry not installed, skip
            pass
        except Exception as e:
            # Log Sentry setup error
            self.logger.error(f"Failed to setup Sentry: {e}")

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message"""
        self._log(LogLevel.ERROR, message, **kwargs)
        if self.sentry_dsn:
            self._capture_to_sentry("error", message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self._log(LogLevel.CRITICAL, message, **kwargs)
        if self.sentry_dsn:
            self._capture_to_sentry("critical", message, **kwargs)

    def _log(self, level: LogLevel, message: str, **kwargs):
        """Internal log method"""
        log_entry = self._create_log_entry(level, message, **kwargs)

        # Log to all handlers
        self.logger.log(getattr(logging, level.value), message, extra=kwargs)

    def _create_log_entry(self, level: LogLevel, message: str, **kwargs) -> Dict[str, Any]:
        """Create structured log entry"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level.value,
            "service": self.service_name,
            "message": message,
            "extra": kwargs or {}
        }

    def _capture_to_sentry(self, level: str, message: str, **kwargs):
        """Send error to Sentry"""
        try:
            import sentry_sdk

            level_map = {
                "error": sentry_sdk.Level.ERROR,
                "critical": sentry_sdk.Level.CRITICAL
            }

            sentry_sdk.capture_exception(
                exception=kwargs.get('exception'),
                level=level_map.get(level, sentry_sdk.Level.ERROR),
                extras=kwargs
            )

        except Exception:
            pass


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
            "extra": getattr(record, 'extra', {})
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self._format_exception(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)

    def _format_exception(self, exc_info) -> str:
        """Format exception info"""
        import traceback
        return {
            "type": exc_info.__class__.__name__,
            "message": str(exc_info),
            "traceback": traceback.format_exc()
        }


class DatabaseLogHandler(logging.Handler):
    """Custom handler to write logs to database"""

    def __init__(self):
        super().__init__()
        self.database_url = None
        self.pool = None

    def emit(self, record: logging.LogRecord):
        """Emit log record to database"""
        if not self.pool:
            # Lazy initialization to avoid circular imports
            import os
            self.database_url = os.getenv('DATABASE_URL')
            if self.database_url:
                import asyncpg
                from typing import Dict, Any

                # Create connection pool
                self.pool = asyncpg.create_pool(
                    self.database_url,
                    min_size=1,
                    max_size=5
                )

        if self.pool:
            import asyncio
            asyncio.create_task(self._write_to_db(record))

    async def _write_to_db(self, record: logging.LogRecord):
        """Write log record to database asynchronously"""
        try:
            log_entry = self._format_record(record)

            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO system_logs (
                        level, message, module, function_name, line_num,
                        extra_data, created_at
                    ) VALUES ($1, $2, $3, $4, $5, NOW())
                """, *log_entry)

        except Exception as e:
            print(f"Failed to write log to database: {e}", file=sys.stderr)

    def _format_record(self, record: logging.LogRecord) -> tuple:
        """Format log record for database"""
        return (
            record.levelname,
            record.getMessage(),
            record.name,
            record.funcName,
            record.lineno,
            json.dumps(getattr(record, 'extra', {}))
        )


# Global logger cache
_loggers: Dict[str, StructuredLogger] = {}


def get_logger(
    service_name: str,
    level: LogLevel = LogLevel.INFO,
    log_format: LogFormat = LogFormat.JSON,
    log_file: Optional[str] = None,
    console_output: bool = True,
    log_to_db: bool = False,
    sentry_dsn: Optional[str] = None
) -> StructuredLogger:
    """
    Get or create logger instance for service

    Args:
        service_name: Name of the service (e.g., 'platform-bot', 'notification-service')
        level: Log level
        log_format: Log output format
        log_file: Path to log file
        console_output: Whether to output to console
        log_to_db: Whether to write logs to database
        sentry_dsn: Sentry DSN for error tracking

    Returns:
        StructuredLogger instance
    """
    if service_name not in _loggers:
        config = LoggerConfig(
            service_name=service_name,
            level=level,
            log_format=log_format,
            log_file=log_file,
            console_output=console_output,
            log_to_db=log_to_db,
            sentry_dsn=sentry_dsn
        )
        _loggers[service_name] = config.get_logger()

    return _loggers[service_name]


def setup_logging(
    service_name: str,
    level: str = "INFO",
    log_format: str = "json",
    log_file: Optional[str] = None,
    log_to_db: bool = False,
    sentry_dsn: Optional[str] = None
) -> StructuredLogger:
    """
    Convenience function to setup logging for a service

    Usage:
        from shared.logging.config import setup_logging

        logger = setup_logging(
            service_name="my-service",
            level=os.getenv("LOG_LEVEL", "INFO"),
            log_format=os.getenv("LOG_FORMAT", "json"),
            log_file=os.getenv("LOG_FILE_PATH"),
            log_to_db=os.getenv("LOG_TO_DB", "false") == "true",
            sentry_dsn=os.getenv("SENTRY_DSN")
        )
    """
    config = LoggerConfig(
        service_name=service_name,
        level=LogLevel(level.upper()) if level.upper() in LogLevel.__members__ else LogLevel.INFO,
        log_format=LogFormat(log_format.lower()) if log_format.lower() in LogFormat.__members__ else LogFormat.JSON,
        log_file=log_file,
        console_output=True,
        log_to_db=log_to_db,
        sentry_dsn=sentry_dsn
    )
    return config.get_logger()
