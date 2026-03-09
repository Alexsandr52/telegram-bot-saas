"""
Global repository instances (singletons)
Initialized on application startup
"""
from typing import Optional

from .db import MasterRepository, BotRepository, SubscriptionRepository, Database


# Global instances
_master_repo: Optional[MasterRepository] = None
_bot_repo: Optional[BotRepository] = None
_subscription_repo: Optional[SubscriptionRepository] = None
_db: Optional[Database] = None


def init_repositories(db: Database) -> None:
    """Initialize repository instances"""
    global _master_repo, _bot_repo, _subscription_repo, _db

    _db = db
    _master_repo = MasterRepository(db)
    _bot_repo = BotRepository(db)
    _subscription_repo = SubscriptionRepository(db)


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


def get_db() -> Database:
    """Get database instance"""
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_repositories first.")
    return _db
