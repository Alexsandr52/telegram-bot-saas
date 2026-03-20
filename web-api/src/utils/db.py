"""
Database connection and queries for Web API
Uses asyncpg for async PostgreSQL operations
"""
import asyncio
import uuid
from datetime import datetime
from typing import Optional, List, Dict
from contextlib import asynccontextmanager
import asyncpg
from loguru import logger


class Database:
    """
    Async PostgreSQL database client using asyncpg
    With retry logic and better error handling
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
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5

    async def connect(self) -> None:
        """Create connection pool with retry logic"""
        if self.pool is not None:
            return  # Already connected

        self._reconnect_attempts = 0
        backoff = asyncio.Sleeper(1, 10, jitter=2)

        while self._reconnect_attempts < self._max_reconnect_attempts:
            try:
                self.pool = await asyncpg.create_pool(
                    self.dsn,
                    min_size=self.min_size,
                    max_size=self.max_size,
                    command_timeout=60,
                    server_settings={'connect_timeout': 10}
                )
                logger.info(f"Database connection pool created (min={self.min_size}, max={self.max_size})")
                return  # Success

            except (asyncpg.PostgresConnectionError, asyncpg.PostgresError) as e:
                self._reconnect_attempts += 1
                wait_time = backoff.delay()

                if self._reconnect_attempts == self._max_reconnect_attempts:
                    logger.error(f"Failed to create database pool after {self._max_reconnect_attempts} attempts: {e}")
                    raise  # Re-raise the exception

                logger.warning(f"Database connection failed (attempt {self._reconnect_attempts}/{self._max_reconnect_attempts}): {e}")
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error(f"Unexpected error creating database pool: {e}")
                raise

    async def close(self) -> None:
        """Close connection pool"""
        if self.pool:
            try:
                await self.pool.close()
                logger.info("Database connection pool closed")
            except Exception as e:
                logger.error(f"Error closing database pool: {e}")
            finally:
                self.pool = None

    @asynccontextmanager
    async def acquire(self):
        """
        Acquire connection from pool with error handling

        Yields:
            connection: asyncpg.Connection
        """
        if self.pool is None:
            await self.connect()

        try:
            async with self.pool.acquire() as conn:
                # Check if connection is still alive
                try:
                    await conn.fetchval('SELECT 1')
                except Exception:
                    # Connection is dead, try to get a new one
                    logger.warning("Connection died, acquiring new one...")
                    raise

                yield conn
        except Exception as e:
            logger.error(f"Error acquiring database connection: {e}")
            raise

    async def execute(self, query: str, *args, timeout: float = None, max_retries: int = 3) -> str:
        """Execute a query with retry logic"""
        for attempt in range(max_retries):
            try:
                async with self.acquire() as conn:
                    return await conn.execute(query, *args, timeout=timeout)
            except (asyncpg.PostgresConnectionError, asyncpg.InterfaceError, asyncpg.OperationalError) as e:
                if attempt == max_retries - 1:
                    logger.error(f"Query failed after {max_retries} attempts: {e}")
                    raise
                logger.warning(f"Query failed (attempt {attempt + 1}/{max_retries}): {e}, retrying...")
                await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff

    async def fetchval(self, query: str, *args, column: int = 0, timeout: float = None, max_retries: int = 3) -> any:
        """Fetch a single value from query result with retry logic"""
        for attempt in range(max_retries):
            try:
                async with self.acquire() as conn:
                    return await conn.fetchval(query, *args, column=column, timeout=timeout)
            except (asyncpg.PostgresConnectionError, asyncpg.InterfaceError, asyncpg.OperationalError) as e:
                if attempt == max_retries - 1:
                    logger.error(f"Query failed after {max_retries} attempts: {e}")
                    raise
                logger.warning(f"Query failed (attempt {attempt + 1}/{max_retries}): {e}, retrying...")
                await asyncio.sleep(1 * (attempt + 1))

    async def fetchrow(self, query: str, *args, timeout: float = None, max_retries: int = 3) -> Optional[asyncpg.Record]:
        """Fetch a single row from query result with retry logic"""
        for attempt in range(max_retries):
            try:
                async with self.acquire() as conn:
                    return await conn.fetchrow(query, *args, timeout=timeout)
            except (asyncpg.PostgresConnectionError, asyncpg.InterfaceError, asyncpg.OperationalError) as e:
                if attempt == max_retries - 1:
                    logger.error(f"Query failed after {max_retries} attempts: {e}")
                    raise
                logger.warning(f"Query failed (attempt {attempt + 1}/{max_retries}): {e}, retrying...")
                await asyncio.sleep(1 * (attempt + 1))

    async def fetch(self, query: str, *args, timeout: float = None, max_retries: int = 3) -> List[asyncpg.Record]:
        """Fetch all rows from query result with retry logic"""
        for attempt in range(max_retries):
            try:
                async with self.acquire() as conn:
                    return await conn.fetch(query, *args, timeout=timeout)
            except (asyncpg.PostgresConnectionError, asyncpg.InterfaceError, asyncpg.OperationalError) as e:
                if attempt == max_retries - 1:
                    logger.error(f"Query failed after {max_retries} attempts: {e}")
                    raise
                logger.warning(f"Query failed (attempt {attempt + 1}/{max_retries}): {e}, retrying...")
                await asyncio.sleep(1 * (attempt + 1))


class Repository:
    """Base repository class"""

    def __init__(self, db: Database):
        self.db = db


class SessionRepository(Repository):
    """Repository for user_sessions operations"""

    async def get_session(self, session_token: str) -> Optional[Dict]:
        """Get session by token"""
        query = """
            SELECT id, master_id, session_token, expires_at, created_at, last_used_at
            FROM user_sessions
            WHERE session_token = $1 AND expires_at > NOW()
        """
        row = await self.db.fetchrow(query, session_token)
        return dict(row) if row else None

    async def update_session_activity(self, session_token: str) -> None:
        """Update session last_used_at"""
        query = """
            UPDATE user_sessions
            SET last_used_at = NOW()
            WHERE session_token = $1
        """
        await self.db.execute(query, session_token)

    async def delete_session(self, session_token: str) -> None:
        """Delete session by token"""
        query = "DELETE FROM user_sessions WHERE session_token = $1"
        await self.db.execute(query, session_token)
        logger.info(f"Session deleted: {session_token}")


class MasterRepository(Repository):
    """Repository for masters operations"""

    async def get_master_by_id(self, master_id: uuid.UUID) -> Optional[Dict]:
        """Get master by ID"""
        query = """
            SELECT id, telegram_id, username, phone, full_name, is_active, created_at
            FROM masters
            WHERE id = $1
        """
        row = await self.db.fetchrow(query, master_id)
        return dict(row) if row else None

    async def get_master_bots(self, master_id: uuid.UUID) -> List[Dict]:
        """Get all bots for a master"""
        query = """
            SELECT id, bot_username, bot_name, business_name, container_status, is_active, created_at
            FROM bots
            WHERE master_id = $1
            ORDER BY created_at DESC
        """
        rows = await self.db.fetch(query, master_id)
        return [dict(row) for row in rows]


class BotRepository(Repository):
    """Repository for bots operations"""

    async def get_bot_by_id(self, bot_id: uuid.UUID) -> Optional[Dict]:
        """Get bot by ID"""
        query = """
            SELECT id, master_id, bot_username, bot_name, business_name, business_description,
                   business_address, business_phone, container_status, is_active,
                   timezone, language, created_at
            FROM bots
            WHERE id = $1
        """
        row = await self.db.fetchrow(query, bot_id)
        return dict(row) if row else None


class ServiceRepository(Repository):
    """Repository for services operations"""

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

    async def create_service(
        self,
        bot_id: uuid.UUID,
        name: str,
        price: float,
        duration_minutes: int,
        description: Optional[str] = None,
        sort_order: int = 0
    ) -> uuid.UUID:
        """Create a new service"""
        query = """
            INSERT INTO services (bot_id, name, description, price, duration_minutes, sort_order)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        """
        service_id = await self.db.fetchval(
            query, bot_id, name, description, price, duration_minutes, sort_order
        )
        logger.info(f"Service created: {service_id}")
        return service_id

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
        """Update service"""
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
        """Delete a service (soft delete)"""
        query = """
            UPDATE services
            SET is_active = false, updated_at = NOW()
            WHERE id = $1
        """
        await self.db.execute(query, service_id)
        logger.info(f"Service deleted: {service_id}")


class ScheduleRepository(Repository):
    """Repository for schedules operations"""

    async def get_bot_schedules(self, bot_id: uuid.UUID) -> List[Dict]:
        """Get schedule for all days of week for a bot"""
        query = """
            SELECT day_of_week, start_time, end_time, is_working_day,
                   break_start_time, break_end_time
            FROM schedules
            WHERE bot_id = $1
            ORDER BY day_of_week
        """
        rows = await self.db.fetch(query, bot_id)
        return [dict(row) for row in rows]

    async def set_schedule(
        self,
        bot_id: uuid.UUID,
        day_of_week: int,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        is_working_day: bool = True,
        break_start_time: Optional[str] = None,
        break_end_time: Optional[str] = None
    ) -> None:
        """Set schedule for a day of week"""
        from datetime import time

        # Convert string times to time objects
        start_time_obj = None
        end_time_obj = None
        break_start_obj = None
        break_end_obj = None

        if start_time:
            h, m, s = map(int, start_time.split(':'))
            start_time_obj = time(h, m, s)

        if end_time:
            h, m, s = map(int, end_time.split(':'))
            end_time_obj = time(h, m, s)

        if break_start_time:
            h, m, s = map(int, break_start_time.split(':'))
            break_start_obj = time(h, m, s)

        if break_end_time:
            h, m, s = map(int, break_end_time.split(':'))
            break_end_obj = time(h, m, s)

        query = """
            INSERT INTO schedules (bot_id, day_of_week, start_time, end_time,
                                  is_working_day, break_start_time, break_end_time)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (bot_id, day_of_week)
            DO UPDATE SET
                start_time = EXCLUDED.start_time,
                end_time = EXCLUDED.end_time,
                is_working_day = EXCLUDED.is_working_day,
                break_start_time = EXCLUDED.break_start_time,
                break_end_time = EXCLUDED.break_end_time,
                updated_at = NOW()
        """
        await self.db.execute(query, bot_id, day_of_week, start_time_obj, end_time_obj,
                             is_working_day, break_start_obj, break_end_obj)
        logger.info(f"Schedule updated for bot {bot_id}, day {day_of_week}")


class AppointmentRepository(Repository):
    """Repository for appointments operations"""

    async def get_bot_appointments(
        self,
        bot_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        status_filter: Optional[str] = None
    ) -> List[Dict]:
        """Get appointments for a bot"""
        if status_filter:
            query = """
                SELECT a.id, a.bot_id, a.start_time, a.end_time, a.status, a.price,
                       c.first_name, c.last_name, c.phone, c.telegram_id,
                       s.name as service_name
                FROM appointments a
                JOIN clients c ON c.id = a.client_id
                JOIN services s ON s.id = a.service_id
                WHERE a.bot_id = $1 AND a.status = $2
                ORDER BY a.start_time DESC
                LIMIT $3 OFFSET $4
            """
            rows = await self.db.fetch(query, bot_id, status_filter, limit, offset)
        else:
            query = """
                SELECT a.id, a.bot_id, a.start_time, a.end_time, a.status, a.price,
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

    async def get_appointment_by_id(self, appointment_id: uuid.UUID) -> Optional[Dict]:
        """Get appointment by ID"""
        query = """
            SELECT a.id, a.bot_id, a.start_time, a.end_time, a.status, a.price,
                   c.first_name, c.last_name, c.phone, c.telegram_id,
                   s.name as service_name
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


# Global database instance
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
