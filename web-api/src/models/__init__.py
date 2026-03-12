"""
Pydantic models for Web API
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


# ============================================
# Auth Models
# ============================================

class LoginRequest(BaseModel):
    """Login request with token from bot"""
    token: str = Field(..., min_length=6, max_length=10)


class LoginResponse(BaseModel):
    """Login response with session info"""
    success: bool
    message: str
    master_id: Optional[str] = None


# ============================================
# Bot Models
# ============================================

class BotResponse(BaseModel):
    """Bot information"""
    id: str
    bot_username: str
    bot_name: Optional[str] = None
    business_name: Optional[str] = None
    container_status: str
    is_active: bool


class BotsListResponse(BaseModel):
    """List of master's bots"""
    bots: list[BotResponse]


# ============================================
# Service Models
# ============================================

class ServiceCreate(BaseModel):
    """Create service request"""
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    duration_minutes: int = Field(..., ge=5, le=480)
    sort_order: int = 0


class ServiceUpdate(BaseModel):
    """Update service request"""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    duration_minutes: Optional[int] = Field(None, ge=5, le=480)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class ServiceResponse(BaseModel):
    """Service information"""
    id: str
    name: str
    description: Optional[str] = None
    price: float
    duration_minutes: int
    is_active: bool
    sort_order: int


class ServicesListResponse(BaseModel):
    """List of bot services"""
    services: list[ServiceResponse]


# ============================================
# Schedule Models
# ============================================

class ScheduleItem(BaseModel):
    """Schedule for a day"""
    day_of_week: int  # 1-7 (Monday-Sunday)
    start_time: str  # HH:MM:SS
    end_time: str  # HH:MM:SS
    is_working_day: bool
    break_start_time: Optional[str] = None
    break_end_time: Optional[str] = None


class ScheduleUpdate(BaseModel):
    """Update schedule request"""
    schedules: list[ScheduleItem]


class ScheduleResponse(BaseModel):
    """Schedule information"""
    schedules: list[ScheduleItem]


# ============================================
# Appointment Models
# ============================================

class AppointmentResponse(BaseModel):
    """Appointment information"""
    id: str
    start_time: datetime
    end_time: datetime
    status: str
    price: float
    client_first_name: Optional[str] = None
    client_last_name: Optional[str] = None
    client_phone: Optional[str] = None
    service_name: str


class AppointmentsListResponse(BaseModel):
    """List of appointments"""
    appointments: list[AppointmentResponse]
    total: int


class AppointmentStatusUpdate(BaseModel):
    """Update appointment status"""
    status: str = Field(..., pattern="^(pending|confirmed|completed|cancelled)$")


# ============================================
# Error Models
# ============================================

class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
