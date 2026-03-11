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


class ServiceRepository:
    """Repository for services table operations"""

    def __init__(self, db: Database):
        self.db = db

    async def create_service(
        self,
        bot_id: uuid.UUID,
        name: str,
        price: float,
        duration_minutes: int,
        description: Optional[str] = None,
        sort_order: int = 0
    ) -> uuid.UUID:
        """Create a new service for a bot"""
        query = """
            INSERT INTO services (bot_id, name, description, price, duration_minutes, sort_order)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        """
        service_id = await self.db.fetchval(
            query, bot_id, name, description, price, duration_minutes, sort_order
        )
        logger.info(f"Service created: {service_id} (bot: {bot_id})")
        return service_id

    async def get_bot_services(self, bot_id: uuid.UUID) -> List[Dict]:
        """Get all services for a bot"""
        query = """
            SELECT id, name, description, price, duration_minutes, is_active, sort_order
            FROM services
            WHERE bot_id = $1
            ORDER BY sort_order, name
        """
        rows = await self.db.fetch(query, bot_id)
        return [dict(row) for row in rows]

    async def get_service(self, service_id: uuid.UUID) -> Optional[Dict]:
        """Get service by ID"""
        query = """
            SELECT id, bot_id, name, description, price, duration_minutes, is_active, sort_order
            FROM services
            WHERE id = $1
        """
        row = await self.db.fetchrow(query, service_id)
        return dict(row) if row else None

    async def update_service(
        self,
        service_id: uuid.UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        price: Optional[float] = None,
        duration_minutes: Optional[int] = None,
        is_active: Optional[bool] = None,
        sort_order: Optional[int] = None
    ) -> None:
        """Update service information"""
        updates = []
        params = []
        param_count = 1

        if name is not None:
            updates.append(f"name = ${param_count}")
            params.append(name)
            param_count += 1

        if description is not None:
            updates.append(f"description = ${param_count}")
            params.append(description)
            param_count += 1

        if price is not None:
            updates.append(f"price = ${param_count}")
            params.append(price)
            param_count += 1

        if duration_minutes is not None:
            updates.append(f"duration_minutes = ${param_count}")
            params.append(duration_minutes)
            param_count += 1

        if is_active is not None:
            updates.append(f"is_active = ${param_count}")
            params.append(is_active)
            param_count += 1

        if sort_order is not None:
            updates.append(f"sort_order = ${param_count}")
            params.append(sort_order)
            param_count += 1

        updates.append("updated_at = NOW()")
        params.append(service_id)

        query = f"""
            UPDATE services
            SET {', '.join(updates)}
            WHERE id = ${param_count}
        """
        await self.db.execute(query, *params)
        logger.info(f"Service updated: {service_id}")

    async def delete_service(self, service_id: uuid.UUID) -> None:
        """Delete a service (soft delete by setting is_active = false)"""
        query = """
            UPDATE services
            SET is_active = false, updated_at = NOW()
            WHERE id = $1
        """
        await self.db.execute(query, service_id)
        logger.info(f"Service deleted: {service_id}")


class AppointmentRepository:
    """Repository for appointments table operations"""

    def __init__(self, db: Database):
        self.db = db

    async def get_bot_appointments(
        self,
        bot_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """Get appointments for a bot"""
        query = """
            SELECT a.id, a.start_time, a.end_time, a.status, a.price,
                   c.first_name, c.last_name, c.phone, c.telegram_id,
                   s.name as service_name
            FROM appointments a
            JOIN clients c ON c.id = a.client_id
            JOIN services s ON s.id = a.service_id
            WHERE a.bot_id = $1
            ORDER BY a.start_time DESC
            LIMIT $2 OFFSET $3
        """
        rows = await self.db.fetch(query, bot_id, limit, offset)
        return [dict(row) for row in rows]

    async def get_appointments_by_date(
        self,
        bot_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime
    ) -> List[Dict]:
        """Get appointments for a bot within date range"""
        query = """
            SELECT a.id, a.start_time, a.end_time, a.status, a.price,
                   c.first_name, c.last_name, c.phone, c.telegram_id,
                   s.name as service_name
            FROM appointments a
            JOIN clients c ON c.id = a.client_id
            JOIN services s ON s.id = a.service_id
            WHERE a.bot_id = $1
                AND a.start_time >= $2
                AND a.start_time <= $3
            ORDER BY a.start_time ASC
        """
        rows = await self.db.fetch(query, bot_id, date_from, date_to)
        return [dict(row) for row in rows]

    async def get_appointment(self, appointment_id: uuid.UUID) -> Optional[Dict]:
        """Get appointment by ID"""
        query = """
            SELECT a.id, a.start_time, a.end_time, a.status, a.price,
                   c.first_name, c.last_name, c.phone, c.telegram_id,
                   s.name as service_name, s.duration_minutes
            FROM appointments a
            JOIN clients c ON c.id = a.client_id
            JOIN services s ON s.id = a.service_id
            WHERE a.id = $1
        """
        row = await self.db.fetchrow(query, appointment_id)
        return dict(row) if row else None

    async def update_appointment_status(
        self,
        appointment_id: uuid.UUID,
        status: str
    ) -> None:
        """Update appointment status"""
        query = """
            UPDATE appointments
            SET status = $2, updated_at = NOW()
            WHERE id = $1
        """
        await self.db.execute(query, appointment_id, status)
        logger.info(f"Appointment status updated: {appointment_id} -> {status}")

    async def get_bot_statistics(
        self,
        bot_id: uuid.UUID
    ) -> Dict:
        """Get statistics for a bot"""
        # Total appointments
        total_count = await self.db.fetchval(
            "SELECT COUNT(*) FROM appointments WHERE bot_id = $1",
            bot_id
        )

        # Appointments by status
        status_counts = await self.db.fetch(
            "SELECT status, COUNT(*) as count FROM appointments WHERE bot_id = $1 GROUP BY status",
            bot_id
        )
        status_stats = {row['status']: row['count'] for row in status_counts}

        # Total revenue
        total_revenue = await self.db.fetchval(
            "SELECT COALESCE(SUM(price), 0) FROM appointments WHERE bot_id = $1 AND status != 'cancelled'",
            bot_id
        ) or 0

        # Unique clients
        unique_clients = await self.db.fetchval(
            "SELECT COUNT(DISTINCT client_id) FROM appointments WHERE bot_id = $1",
            bot_id
        )

        return {
            'total_appointments': total_count,
            'status_breakdown': status_stats,
            'total_revenue': float(total_revenue),
            'unique_clients': unique_clients
        }


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


class ScheduleRepository:
    """Repository for schedules table operations"""

    def __init__(self, db: Database):
        self.db = db

    async def get_bot_schedules(self, bot_id: uuid.UUID) -> List[Dict]:
        """Get schedule for all days of week for a bot"""
        query = """
            SELECT day_of_week, start_time, end_time, is_available
            FROM schedules
            WHERE bot_id = $1
            ORDER BY day_of_week
        """
        rows = await self.db.fetch(query, bot_id)
        return rows

    async def get_schedule_for_day(
        self, bot_id: uuid.UUID, day_of_week: int
    ) -> Optional[Dict]:
        """Get schedule for specific day of week"""
        query = """
            SELECT day_of_week, start_time, end_time, is_available
            FROM schedules
            WHERE bot_id = $1 AND day_of_week = $2
        """
        row = await self.db.fetchrow(query, bot_id, day_of_week)
        return row

    async def set_schedule(
        self,
        bot_id: uuid.UUID,
        day_of_week: int,
        start_time: str,
        end_time: str,
        is_available: bool = True
    ) -> None:
        """Set schedule for a day of week"""
        query = """
            INSERT INTO schedules (bot_id, day_of_week, start_time, end_time, is_available)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (bot_id, day_of_week)
            DO UPDATE SET
                start_time = EXCLUDED.start_time,
                end_time = EXCLUDED.end_time,
                is_available = EXCLUDED.is_available,
                updated_at = NOW()
        """
        await self.db.execute(query, bot_id, day_of_week, start_time, end_time, is_available)
        logger.info(f"Schedule updated for bot {bot_id}, day {day_of_week}")

    async def set_day_unavailable(self, bot_id: uuid.UUID, day_of_week: int) -> None:
        """Mark a day as unavailable (day off)"""
        query = """
            INSERT INTO schedules (bot_id, day_of_week, start_time, end_time, is_available)
            VALUES ($1, $2, '00:00:00', '00:00:00', false)
            ON CONFLICT (bot_id, day_of_week)
            DO UPDATE SET is_available = false, updated_at = NOW()
        """
        await self.db.execute(query, bot_id, day_of_week)
        logger.info(f"Day {day_of_week} marked as unavailable for bot {bot_id}")
