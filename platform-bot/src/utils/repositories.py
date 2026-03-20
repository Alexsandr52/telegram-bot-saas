"""
Repository initialization for Platform Bot
"""
from loguru import logger


def init_repositories(db):
    """Initialize all repositories with database connection"""
    # TODO: Implement repository initialization
    # This will be implemented when we add repository classes
    pass


# Singleton repository instances
_master_repo = None
_bot_repo = None
_subscription_repo = None
_service_repo = None
_appointment_repo = None
_schedule_repo = None
_session_repo = None


def get_master_repo():
    """Get or create master repository singleton"""
    global _master_repo
    if _master_repo is None:
        from src.utils.db import MasterRepository, Database
        from src.utils.config import get_settings
        db = Database(get_settings().DATABASE_URL)
        _master_repo = MasterRepository(db)
    return _master_repo


def get_bot_repo():
    """Get or create bot repository singleton"""
    global _bot_repo
    if _bot_repo is None:
        from src.utils.db import BotRepository, Database
        from src.utils.config import get_settings
        db = Database(get_settings().DATABASE_URL)
        _bot_repo = BotRepository(db)
    return _bot_repo


def get_subscription_repo():
    """Get or create subscription repository singleton"""
    global _subscription_repo
    if _subscription_repo is None:
        from src.utils.db import SubscriptionRepository, Database
        from src.utils.config import get_settings
        db = Database(get_settings().DATABASE_URL)
        _subscription_repo = SubscriptionRepository(db)
    return _subscription_repo


def get_service_repo():
    """Get or create service repository singleton"""
    global _service_repo
    if _service_repo is None:
        from src.utils.db import ServiceRepository, Database
        from src.utils.config import get_settings
        db = Database(get_settings().DATABASE_URL)
        _service_repo = ServiceRepository(db)
    return _service_repo


def get_appointment_repo():
    """Get or create appointment repository singleton"""
    global _appointment_repo
    if _appointment_repo is None:
        from src.utils.db import AppointmentRepository, Database
        from src.utils.config import get_settings
        db = Database(get_settings().DATABASE_URL)
        _appointment_repo = AppointmentRepository(db)
    return _appointment_repo


def get_schedule_repo():
    """Get or create schedule repository singleton"""
    global _schedule_repo
    if _schedule_repo is None:
        from src.utils.db import ScheduleRepository, Database
        from src.utils.config import get_settings
        db = Database(get_settings().DATABASE_URL)
        _schedule_repo = ScheduleRepository(db)
    return _schedule_repo


def get_session_repo():
    """Get or create session repository singleton"""
    global _session_repo
    if _session_repo is None:
        from src.utils.db import SessionRepository, Database
        from src.utils.config import get_settings
        db = Database(get_settings().DATABASE_URL)
        _session_repo = SessionRepository(db)
    return _session_repo
