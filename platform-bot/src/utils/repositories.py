"""
Global repository instances (singletons)
Initialized on application startup
"""
from typing import Optional

from .db import (
    MasterRepository,
    BotRepository,
    SubscriptionRepository,
    ServiceRepository,
    AppointmentRepository,
    ScheduleRepository,
    SessionRepository,
    Database
)


# Global instances
_master_repo: Optional[MasterRepository] = None
_bot_repo: Optional[BotRepository] = None
_subscription_repo: Optional[SubscriptionRepository] = None
_service_repo: Optional[ServiceRepository] = None
_appointment_repo: Optional[AppointmentRepository] = None
_schedule_repo: Optional[ScheduleRepository] = None
_session_repo: Optional[SessionRepository] = None
_db: Optional[Database] = None


def init_repositories(db: Database) -> None:
    """Initialize repository instances"""
    global _master_repo, _bot_repo, _subscription_repo, _service_repo, _appointment_repo, _schedule_repo, _session_repo, _db

    _db = db
    _master_repo = MasterRepository(db)
    _bot_repo = BotRepository(db)
    _subscription_repo = SubscriptionRepository(db)
    _service_repo = ServiceRepository(db)
    _appointment_repo = AppointmentRepository(db)
    _schedule_repo = ScheduleRepository(db)
    _session_repo = SessionRepository(db)


def get_master_repo() -> MasterRepository:
    """Get master repository instance"""
    if _master_repo is None:
        raise RuntimeError("Master repository not initialized. Call init_repositories first.")
    return _master_repo


def get_bot_repo() -> BotRepository:
    """Get bot repository instance"""
    if _bot_repo is None:
        raise RuntimeError("Bot repository not initialized. Call init_repositories first.")
    return _bot_repo


def get_subscription_repo() -> SubscriptionRepository:
    """Get subscription repository instance"""
    if _subscription_repo is None:
        raise RuntimeError("Subscription repository not initialized. Call init_repositories first.")
    return _subscription_repo


def get_service_repo() -> ServiceRepository:
    """Get service repository instance"""
    if _service_repo is None:
        raise RuntimeError("Service repository not initialized. Call init_repositories first.")
    return _service_repo


def get_appointment_repo() -> AppointmentRepository:
    """Get appointment repository instance"""
    if _appointment_repo is None:
        raise RuntimeError("Appointment repository not initialized. Call init_repositories first.")
    return _appointment_repo


def get_schedule_repo() -> ScheduleRepository:
    """Get schedule repository instance"""
    if _schedule_repo is None:
        raise RuntimeError("Schedule repository not initialized. Call init_repositories first.")
    return _schedule_repo


def get_session_repo() -> SessionRepository:
    """Get session repository instance"""
    if _session_repo is None:
        raise RuntimeError("Session repository not initialized. Call init_repositories first.")
    return _session_repo


def get_db() -> Database:
    """Get database instance"""
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_repositories first.")
    return _db
