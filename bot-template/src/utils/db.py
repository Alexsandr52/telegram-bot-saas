"""
Database operations for Bot Template
Handles clients, appointments, and availability checks
"""
import asyncio
from datetime import datetime, timedelta, time
from typing import Optional, List
from decimal import Decimal
from loguru import logger

import asyncpg


class BotDatabase:
    """
    Database client for bot operations
    Works with the main bot_saas database
    """

    def __init__(self, database_url: str, bot_id: str):
        """
        Initialize database client

        Args:
            database_url: PostgreSQL connection string
            bot_id: Bot UUID
        """
        self.database_url = database_url
        self.bot_id = bot_id
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self, min_size: int = 5, max_size: int = 10) -> None:
        """Create connection pool"""
        self._pool = await asyncpg.create_pool(
            self.database_url,
            min_size=min_size,
            max_size=max_size,
            command_timeout=60
        )
        logger.info(f"Database connected for bot {self.bot_id}")

    async def close(self) -> None:
        """Close connection pool"""
        if self._pool:
            await self._pool.close()
            logger.info("Database connection closed")

    async def execute(self, query: str, *args) -> str:
        """Execute a query"""
        async with self._pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetchval(self, query: str, *args, column: int = 0):
        """Fetch a single value"""
        async with self._pool.acquire() as conn:
            return await conn.fetchval(query, *args, column=column)

    async def fetchrow(self, query: str, *args):
        """Fetch a single row"""
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetch(self, query: str, *args) -> List:
        """Fetch all rows"""
        async with self._pool.acquire() as conn:
            return await conn.fetch(query, *args)

    # ============================================
    # Clients
    # ============================================

    async def get_or_create_client(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> dict:
        """
        Get existing client or create new one

        Returns:
            Client data dict
        """
        client = await self.fetchrow(
            """
            SELECT id, telegram_id, username, first_name, last_name,
                   phone, email, notes, total_visits, total_spent
            FROM clients
            WHERE bot_id = $1 AND telegram_id = $2
            """,
            self.bot_id, telegram_id
        )

        if client:
            return dict(client)

        # Create new client
        client_id = await self.fetchval(
            """
            INSERT INTO clients (bot_id, telegram_id, username, first_name, last_name)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            self.bot_id, telegram_id, username, first_name, last_name
        )

        return {
            'id': client_id,
            'telegram_id': telegram_id,
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'total_visits': 0,
            'total_spent': Decimal('0')
        }

    async def update_client_phone(self, client_id: str, phone: str) -> None:
        """Update client phone number"""
        await self.execute(
            """
            UPDATE clients
            SET phone = $2
            WHERE id = $1
            """,
            client_id, phone
        )

    # ============================================
    # Appointments
    # ============================================

    async def check_slot_availability(
        self,
        service_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> bool:
        """
        Check if time slot is available

        Args:
            service_id: Service UUID
            start_time: Start time
            end_time: End time

        Returns:
            True if slot is available
        """
        count = await self.fetchval(
            """
            SELECT COUNT(*)
            FROM appointments
            WHERE bot_id = $1
                AND start_time < $3
                AND end_time > $2
                AND status IN ('pending', 'confirmed')
            """,
            self.bot_id, start_time, end_time
        )

        return count == 0

    async def get_available_slots(
        self,
        service_id: str,
        date: datetime
    ) -> List[dict]:
        """
        Get available time slots for a service on specific date

        Args:
            service_id: Service UUID
            date: Date to check

        Returns:
            List of available slots with times
        """
        # Get service duration
        service = await self.fetchrow(
            "SELECT duration_minutes FROM services WHERE id = $1",
            service_id
        )

        if not service:
            return []

        duration = service['duration_minutes']

        # Get schedule for the day
        weekday = date.weekday()  # 0 = Monday in Python
        schedule = await self.fetchrow(
            """
            SELECT start_time, end_time, is_working_day,
                   break_start_time, break_end_time
            FROM schedules
            WHERE bot_id = $1 AND day_of_week = $2
            """,
            self.bot_id, weekday
        )

        if not schedule or not schedule['is_working_day']:
            return []

        # Generate slots
        start_time = datetime.combine(date.date(), schedule['start_time'])
        end_time = datetime.combine(date.date(), schedule['end_time'])

        # Handle break time
        if schedule['break_start_time'] and schedule['break_end_time']:
            break_start = datetime.combine(date.date(), schedule['break_start_time'])
            break_end = datetime.combine(date.date(), schedule['break_end_time'])
        else:
            break_start = None
            break_end = None

        slots = []
        current = start_time
        slot_duration = timedelta(minutes=30)  # 30-minute slots

        while current + timedelta(minutes=duration) <= end_time:
            slot_end = current + timedelta(minutes=duration)

            # Skip if in break time
            if break_start and break_end:
                if current >= break_start and slot_end <= break_end:
                    current += slot_duration
                    continue

            # Check availability
            is_available = await self.check_slot_availability(service_id, current, slot_end)

            slots.append({
                'start_time': current,
                'end_time': slot_end,
                'is_available': is_available
            })

            current += slot_duration

        return slots

    async def create_appointment(
        self,
        client_id: str,
        service_id: str,
        start_time: datetime,
        end_time: datetime,
        price: Decimal,
        comment: Optional[str] = None
    ) -> str:
        """
        Create a new appointment

        Returns:
            Appointment ID
        """
        appointment_id = await self.fetchval(
            """
            INSERT INTO appointments
            (bot_id, client_id, service_id, start_time, end_time,
             price, status, comment)
            VALUES ($1, $2, $3, $4, $5, $6, 'pending', $7)
            RETURNING id
            """,
            self.bot_id, client_id, service_id, start_time, end_time,
            price, comment
        )

        logger.info(f"Appointment created: {appointment_id} for client {client_id}")
        return appointment_id

    async def get_appointment(self, appointment_id: str) -> Optional[dict]:
        """Get appointment by ID with full info"""
        row = await self.fetchrow(
            """
            SELECT a.id, a.start_time, a.end_time, a.status, a.price,
                   a.comment, a.created_at,
                   s.name as service_name, s.duration_minutes,
                   c.first_name, c.last_name, c.phone
            FROM appointments a
            JOIN services s ON s.id = a.service_id
            JOIN clients c ON c.id = a.client_id
            WHERE a.id = $1
            """,
            appointment_id
        )

        return dict(row) if row else None

    async def get_client_appointments(
        self,
        client_id: str,
        status: Optional[str] = None,
        upcoming_only: bool = False,
        limit: int = 10,
        offset: int = 0
    ) -> List[dict]:
        """
        Get client appointments with filtering options

        Args:
            client_id: Client UUID
            status: Filter by status (pending/confirmed/completed/cancelled)
            upcoming_only: Only show future appointments
            limit: Max number of appointments
            offset: Pagination offset

        Returns:
            List of appointment dicts
        """
        conditions = ["a.client_id = $1"]
        params = [client_id]
        param_count = 1

        if status:
            param_count += 1
            conditions.append(f"a.status = ${param_count}")
            params.append(status)

        if upcoming_only:
            param_count += 1
            conditions.append(f"a.start_time > NOW()")

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT a.id, a.start_time, a.end_time, a.status,
                   s.name as service_name, s.price, s.duration_minutes
            FROM appointments a
            JOIN services s ON s.id = a.service_id
            WHERE {where_clause}
            ORDER BY a.start_time ASC
            LIMIT ${param_count + 1} OFFSET ${param_count + 2}
        """
        params.extend([limit, offset])

        rows = await self.fetch(query, *params)
        return [dict(row) for row in rows]

    async def get_upcoming_appointments(
        self,
        client_id: str,
        limit: int = 5
    ) -> List[dict]:
        """Get upcoming appointments for a client"""
        return await self.get_client_appointments(
            client_id=client_id,
            upcoming_only=True,
            limit=limit
        )

    async def get_past_appointments(
        self,
        client_id: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[dict]:
        """Get past appointments for a client"""
        rows = await self.fetch(
            """
            SELECT a.id, a.start_time, a.end_time, a.status,
                   s.name as service_name, s.price, s.duration_minutes
            FROM appointments a
            JOIN services s ON s.id = a.service_id
            WHERE a.client_id = $1 AND a.start_time < NOW()
            ORDER BY a.start_time DESC
            LIMIT $2 OFFSET $3
            """,
            client_id, limit, offset
        )
        return [dict(row) for row in rows]

    async def cancel_appointment(
        self,
        appointment_id: str,
        client_id: str
    ) -> bool:
        """
        Cancel an appointment

        Args:
            appointment_id: Appointment UUID
            client_id: Client UUID (for verification)

        Returns:
            True if cancelled successfully
        """
        result = await self.execute(
            """
            UPDATE appointments
            SET status = 'cancelled',
                updated_at = NOW()
            WHERE id = $1
              AND client_id = $2
              AND start_time > NOW()
              AND status IN ('pending', 'confirmed')
            """,
            appointment_id, client_id
        )

        # Check if row was updated
        return "UPDATE 1" in result or "UPDATE 0" not in result

    # ============================================
    # Services
    # ============================================

    async def get_active_services(self) -> List[dict]:
        """Get all active services for this bot"""
        rows = await self.fetch(
            """
            SELECT id, name, description, price, duration_minutes, photo_url
            FROM services
            WHERE bot_id = $1 AND is_active = true
            ORDER BY sort_order
            """,
            self.bot_id
        )

        return [dict(row) for row in rows]

    async def get_service(self, service_id: str) -> Optional[dict]:
        """Get service by ID"""
        row = await self.fetchrow(
            """
            SELECT id, name, description, price, duration_minutes,
                   photo_url, settings
            FROM services
            WHERE id = $1
            """,
            service_id
        )

        return dict(row) if row else None

    # ============================================
    # Analytics (optional)
    # ============================================

    async def log_analytics_event(
        self,
        event_type: str,
        user_id: int,
        event_data: dict = None
    ) -> None:
        """Log analytics event"""
        await self.execute(
            """
            INSERT INTO analytics_events (bot_id, event_type, user_id, event_data)
            VALUES ($1, $2, $3, $4)
            """,
            self.bot_id, event_type, user_id, event_data or {}
        )


# Global database instance
_db: Optional[BotDatabase] = None


def get_database() -> Optional[BotDatabase]:
    """Get global database instance"""
    return _db


def set_database(db: BotDatabase) -> None:
    """Set global database instance"""
    global _db
    _db = db
