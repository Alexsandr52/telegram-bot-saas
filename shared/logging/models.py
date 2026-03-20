"""
Logging API Models
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class LogLevel(str, str):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogQuery(BaseModel):
    """Query parameters for log retrieval"""
    level: Optional[LogLevel] = None
    service: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 100
    offset: int = 0
    search: Optional[str] = None


class LogEntry(BaseModel):
    """Log entry model"""
    id: str
    level: str
    service: str
    logger: Optional[str] = None
    function_name: Optional[str] = None
    line_num: Optional[int] = None
    message: str
    extra_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    class Config:
        from_attributes = True


class LogStats(BaseModel):
    """Log statistics"""
    total_logs: int
    by_level: Dict[str, int]
    by_service: Dict[str, int]
    time_range: Dict[str, datetime]


class LogLevelCount(BaseModel):
    """Log level count"""
    level: str
    count: int
    percentage: float


class ServiceLogStats(BaseModel):
    """Service log statistics"""
    service: str
    total_logs: int
    error_count: int
    warning_count: int
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None


class LogExportRequest(BaseModel):
    """Log export request"""
    service: Optional[str] = None
    level: Optional[LogLevel] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    format: str = "json"  # json, csv


class LogCleanupRequest(BaseModel):
    """Log cleanup request"""
    older_than_days: int = 30  # Default: keep last 30 days
