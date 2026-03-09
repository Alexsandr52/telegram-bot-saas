"""
Database connection and queries for Platform Bot
Uses asyncpg for async PostgreSQL operations
"""
import asyncio
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import asyncpg
from loguru import logger


class Database:
    """
    Async PostgreSQL database client using asyncpg

    Usage:
        db = Database(dsn="postgresql://user:pass@host:port/db")
        await db.connect()

        result = await db.fetchval("SELECT ...")
        await db.execute("INSERT INTO ...")

        await db.close()
    """

    def __init__(self, dsn: str, min_size: int = 10, max_size: int = 20):
        """
        Initialize database connection pool

        Args:
            dsn: PostgreSQL connection string
            min_size: Minimum pool size
            max_size: Maximum pool size
        """
        self.dsn = dsn
        self.min_size = min_size
        self.max_size = max_size
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """Create connection pool"""
        if self.pool is None:
            try:
                self.pool = await asyncpg.create_pool(
                    self.dsn,
                    min_size=self.min_size,
                    max_size=self.max_size,
                    command_timeout=60,
                )
                logger.info("Database connection pool created")
            except Exception as e:
                logger.error(f"Failed to create database pool: {e}")
                raise

    async def close(self) -> None:
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Database connection pool closed")

    @asynccontextmanager
    async def acquire(self):
        """
        Acquire connection from pool

        Usage:
            async with db.acquire() as conn:
                result = await conn.fetchval("SELECT ...")
        """
        if self.pool is None:
            await self.connect()

        async with self.pool.acquire() as connection:
            yield connection

    async def execute(self, query: str, *args, timeout: float = None) -> str:
        """
        Execute a query that doesn't return data

        Args:
            query: SQL query
            *args: Query parameters
            timeout: Query timeout in seconds

        Returns:
            Execution status string
        """
        async with self.acquire() as conn:
            return await conn.execute(query, *args, timeout=timeout)

    async def executemany(self, command: str, args, timeout: float = None) -> str:
        """
        Execute command multiple times with different parameter sets

        Args:
            command: SQL command
            args: Iterable of parameter sets
            timeout: Query timeout in seconds

        Returns:
            Execution status string
        """
        async with self.acquire() as conn:
            return await conn.executemany(command, args, timeout=timeout)

    async def fetchval(self, query: str, *args, column: int = 0, timeout: float = None) -> Any:
        """
        Fetch a single value from query result

        Args:
            query: SQL query
            *args: Query parameters
            column: Column index to return
            timeout: Query timeout in seconds

        Returns:
            Single value or None
        """
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args, column=column, timeout=timeout)

    async def fetchrow(self, query: str, *args, timeout: float = None) -> Optional[asyncpg.Record]:
        """
        Fetch a single row from query result

        Args:
            query: SQL query
            *args: Query parameters
            timeout: Query timeout in seconds

        Returns:
            Record object or None
        """
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args, timeout=timeout)

    async def fetch(self, query: str, *args, timeout: float = None) -> List[asyncpg.Record]:
        """
        Fetch all rows from query result

        Args:
            query: SQL query
            *args: Query parameters
            timeout: Query timeout in seconds

        Returns:
            List of Record objects
        """
        async with self.acquire() as conn:
            return await conn.fetch(query, *args, timeout=timeout)

    async def transaction(self):
        """
        Start a transaction

        Usage:
            async with db.transaction() as conn:
                await conn.execute("INSERT INTO ...")
                await conn.execute("UPDATE ...")
        """
        async with self.acquire() as conn:
            async with conn.transaction():
                yield conn


# ============================================
# Repository Classes
# ============================================

class MasterRepository:
    """Repository for masters table operations"""

    def __init__(self, db: Database):
        self.db = db

    async def create_master(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
        phone: Optional[str] = None
    ) -> uuid.UUID:
        """
        Create a new master

        Returns:
            Master ID (UUID)
        """
        query = """
            INSERT INTO masters (telegram_id, username, full_name, phone)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (telegram_id) DO UPDATE
                SET username = COALESCE(EXCLUDED.username, masters.username),
                    full_name = COALESCE(EXCLUDED.full_name, masters.full_name),
                    phone = COALESCE(EXCLUDED.phone, masters.phone),
                    updated_at = NOW()
            RETURNING id
        """
        master_id = await self.db.fetchval(
            query,
            telegram_id,
            username,
            full_name,
            phone
        )
        logger.info(f"Master created/updated: {master_id} (telegram_id: {telegram_id})")
        return master_id

    async def get_master_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """Get master by Telegram ID"""
        query = """
            SELECT id, telegram_id, username, phone, full_name, is_active, created_at
            FROM masters
            WHERE telegram_id = $1
        """
        row = await self.db.fetchrow(query, telegram_id)
        return dict(row) if row else None

    async def get_master_by_id(self, master_id: uuid.UUID) -> Optional[Dict]:
        """Get master by ID"""
        query = """
            SELECT id, telegram_id, username, phone, full_name, is_active, created_at
            FROM masters
            WHERE id = $1
        """
        row = await self.db.fetchrow(query, master_id)
        return dict(row) if row else None

    async def update_master(
        self,
        master_id: uuid.UUID,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
        phone: Optional[str] = None
    ) -> None:
        """Update master information"""
        query = """
            UPDATE masters
            SET
                username = COALESCE($2, username),
                full_name = COALESCE($3, full_name),
                phone = COALESCE($4, phone),
                updated_at = NOW()
            WHERE id = $1
        """
        await self.db.execute(query, master_id, username, full_name, phone)
        logger.info(f"Master updated: {master_id}")


class BotRepository:
    """Repository for bots table operations"""

    def __init__(self, db: Database):
        self.db = db

    async def create_bot(
        self,
        master_id: uuid.UUID,
        bot_token: str,
        bot_username: str,
        bot_name: Optional[str] = None
    ) -> uuid.UUID:
        """
        Create a new bot for a master

        Returns:
            Bot ID (UUID)
        """
        query = """
            INSERT INTO bots (master_id, bot_token, bot_username, bot_name, container_status)
            VALUES ($1, $2, $3, $4, 'creating')
            RETURNING id
        """
        bot_id = await self.db.fetchval(query, master_id, bot_token, bot_username, bot_name)
        logger.info(f"Bot created: {bot_id} (@{bot_username})")
        return bot_id

    async def get_bot_by_id(self, bot_id: uuid.UUID) -> Optional[Dict]:
        """Get bot by ID"""
        query = """
            SELECT id, master_id, bot_username, bot_name, business_name,
                   container_status, container_id, is_active, created_at
            FROM bots
            WHERE id = $1
        """
        row = await self.db.fetchrow(query, bot_id)
        return dict(row) if row else None

    async def get_bot_by_username(self, bot_username: str) -> Optional[Dict]:
        """Get bot by username"""
        query = """
            SELECT id, master_id, bot_username, bot_name, business_name,
                   container_status, container_id, is_active, created_at
            FROM bots
            WHERE bot_username = $1
        """
        row = await self.db.fetchrow(query, bot_username)
        return dict(row) if row else None

    async def get_master_bots(self, master_id: uuid.UUID) -> List[Dict]:
        """Get all bots for a master"""
        query = """
            SELECT id, bot_username, bot_name, business_name,
                   container_status, is_active, created_at
            FROM bots
            WHERE master_id = $1
            ORDER BY created_at DESC
        """
        rows = await self.db.fetch(query, master_id)
        return [dict(row) for row in rows]

    async def update_bot_container(
        self,
        bot_id: uuid.UUID,
        container_id: str,
        container_status: str
    ) -> None:
        """Update bot container information"""
        query = """
            UPDATE bots
            SET container_id = $2,
                container_status = $3,
                updated_at = NOW()
            WHERE id = $1
        """
        await self.db.execute(query, bot_id, container_id, container_status)
        logger.info(f"Bot container updated: {bot_id} -> {container_id} ({container_status})")

    async def set_bot_webhook(
        self,
        bot_id: uuid.UUID,
        webhook_url: str,
        webhook_secret: str
    ) -> None:
        """Set bot webhook URL and secret"""
        query = """
            UPDATE bots
            SET webhook_url = $2,
                webhook_secret = $3,
                updated_at = NOW()
            WHERE id = $1
        """
        await self.db.execute(query, bot_id, webhook_url, webhook_secret)
        logger.info(f"Bot webhook set: {bot_id} -> {webhook_url}")


class SubscriptionRepository:
    """Repository for subscriptions table operations"""

    def __init__(self, db: Database):
        self.db = db

    async def get_active_subscription(self, master_id: uuid.UUID) -> Optional[Dict]:
        """Get active subscription for a master"""
        query = """
            SELECT id, master_id, plan, status, bots_limit, appointments_limit,
                   starts_at, expires_at, auto_renew
            FROM subscriptions
            WHERE master_id = $1
                AND status = 'active'
                AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY created_at DESC
            LIMIT 1
        """
        row = await self.db.fetchrow(query, master_id)
        return dict(row) if row else None

    async def can_create_bot(self, master_id: uuid.UUID) -> bool:
        """Check if master can create more bots based on subscription"""
        subscription = await self.get_active_subscription(master_id)

        if not subscription:
            # Free tier: 1 bot
            subscription = {'bots_limit': 1}
        elif subscription['bots_limit'] is None:
            # Unlimited bots
            return True

        # Count active bots
        bot_count = await self.db.fetchval(
            "SELECT COUNT(*) FROM bots WHERE master_id = $1 AND is_active = true",
            master_id
        )

        return bot_count < subscription['bots_limit']


# ============================================
# Global Database Instance
# ============================================

_db: Optional[Database] = None


def get_database(dsn: str, min_size: int = 10, max_size: int = 20) -> Database:
    """Get global database instance"""
    global _db
    if _db is None:
        _db = Database(dsn, min_size, max_size)
    return _db


async def init_database(dsn: str) -> Database:
    """Initialize database connection"""
    db = get_database(dsn)
    await db.connect()
    return db


async def close_database() -> None:
    """Close database connection"""
    global _db
    if _db:
        await _db.close()
