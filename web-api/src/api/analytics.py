"""
Analytics API endpoints
Provide statistics and metrics for bots and masters
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from loguru import logger

from ..utils.db import Database, get_database
from ..api.auth import get_current_master


router = APIRouter(prefix="/analytics", tags=["analytics"])


# ============================================
# Pydantic Models
# ============================================

class BotOverviewResponse(BaseModel):
    """Bot overview statistics"""
    bot_id: str
    bot_name: str
    total_appointments: int
    completed_appointments: int
    cancelled_appointments: int
    total_revenue: float
    unique_clients: int
    active_services: int
    period_start: datetime
    period_end: datetime


class RevenueDataPoint(BaseModel):
    """Single revenue data point"""
    date: str
    revenue: float
    appointments: int


class RevenueResponse(BaseModel):
    """Revenue statistics"""
    bot_id: str
    bot_name: str
    total_revenue: float
    period_revenue: float
    period_appointments: int
    period_start: datetime
    period_end: datetime
    daily_data: List[RevenueDataPoint]


class AppointmentsStats(BaseModel):
    """Appointments statistics"""
    bot_id: str
    bot_name: str
    total: int
    pending: int
    confirmed: int
    completed: int
    cancelled: int
    conversion_rate: float  # confirmed / total * 100


class MasterOverviewResponse(BaseModel):
    """Master overview statistics"""
    master_id: str
    total_bots: int
    active_bots: int
    total_appointments: int
    total_revenue: float
    unique_clients: int


class LogEventRequest(BaseModel):
    """Request to log analytics event"""
    bot_id: Optional[str] = None
    event_type: str
    user_id: Optional[int] = None
    event_data: Optional[Dict[str, Any]] = None


# ============================================
# Bot Analytics Endpoints
# ============================================

@router.get("/bots/{bot_id}/overview", response_model=BotOverviewResponse)
async def get_bot_overview(
    bot_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Database = Depends(get_database),
    current_master: dict = Depends(get_current_master)
) -> BotOverviewResponse:
    """
    Get overview statistics for a specific bot

    Args:
        bot_id: Bot UUID
        days: Number of days to analyze (1-365)

    Returns:
        Bot overview statistics
    """
    try:
        # Verify bot ownership
        bot_uuid = uuid.UUID(bot_id)
        bot = await db.fetchrow(
            "SELECT id, bot_name FROM bots WHERE id = $1 AND master_id = $2",
            bot_uuid,
            current_master['id']
        )

        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")

        period_start = datetime.now() - timedelta(days=days)
        period_end = datetime.now()

        # Get total appointments
        total_appointments = await db.fetchval(
            """
            SELECT COUNT(*)
            FROM appointments
            WHERE bot_id = $1 AND created_at >= $2 AND created_at <= $3
            """,
            bot_uuid,
            period_start,
            period_end
        )

        # Get completed appointments
        completed_appointments = await db.fetchval(
            """
            SELECT COUNT(*)
            FROM appointments
            WHERE bot_id = $1 AND status = 'completed'
              AND created_at >= $2 AND created_at <= $3
            """,
            bot_uuid,
            period_start,
            period_end
        )

        # Get cancelled appointments
        cancelled_appointments = await db.fetchval(
            """
            SELECT COUNT(*)
            FROM appointments
            WHERE bot_id = $1 AND status = 'cancelled'
              AND created_at >= $2 AND created_at <= $3
            """,
            bot_uuid,
            period_start,
            period_end
        )

        # Get total revenue
        total_revenue = await db.fetchval(
            """
            SELECT COALESCE(SUM(price), 0)
            FROM appointments
            WHERE bot_id = $1 AND status IN ('completed', 'confirmed')
              AND created_at >= $2 AND created_at <= $3
            """,
            bot_uuid,
            period_start,
            period_end
        ) or 0.0

        # Get unique clients
        unique_clients = await db.fetchval(
            """
            SELECT COUNT(DISTINCT client_id)
            FROM appointments
            WHERE bot_id = $1 AND created_at >= $2 AND created_at <= $3
            """,
            bot_uuid,
            period_start,
            period_end
        )

        # Get active services
        active_services = await db.fetchval(
            """
            SELECT COUNT(*)
            FROM services
            WHERE bot_id = $1 AND is_active = true
            """,
            bot_uuid
        )

        return BotOverviewResponse(
            bot_id=str(bot_uuid),
            bot_name=bot['bot_name'],
            total_appointments=total_appointments,
            completed_appointments=completed_appointments,
            cancelled_appointments=cancelled_appointments,
            total_revenue=float(total_revenue),
            unique_clients=unique_clients,
            active_services=active_services,
            period_start=period_start,
            period_end=period_end
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bot overview: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/bots/{bot_id}/revenue", response_model=RevenueResponse)
async def get_bot_revenue(
    bot_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Database = Depends(get_database),
    current_master: dict = Depends(get_current_master)
) -> RevenueResponse:
    """
    Get revenue statistics for a specific bot

    Args:
        bot_id: Bot UUID
        days: Number of days to analyze (1-365)

    Returns:
        Revenue statistics with daily breakdown
    """
    try:
        bot_uuid = uuid.UUID(bot_id)

        # Verify bot ownership
        bot = await db.fetchrow(
            "SELECT id, bot_name FROM bots WHERE id = $1 AND master_id = $2",
            bot_uuid,
            current_master['id']
        )

        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")

        period_start = datetime.now() - timedelta(days=days)
        period_end = datetime.now()

        # Get period revenue
        period_revenue = await db.fetchval(
            """
            SELECT COALESCE(SUM(price), 0)
            FROM appointments
            WHERE bot_id = $1 AND status IN ('completed', 'confirmed')
              AND created_at >= $2 AND created_at <= $3
            """,
            bot_uuid,
            period_start,
            period_end
        ) or 0.0

        # Get total revenue (all time)
        total_revenue = await db.fetchval(
            """
            SELECT COALESCE(SUM(price), 0)
            FROM appointments
            WHERE bot_id = $1 AND status IN ('completed', 'confirmed')
            """,
            bot_uuid
        ) or 0.0

        # Get period appointments
        period_appointments = await db.fetchval(
            """
            SELECT COUNT(*)
            FROM appointments
            WHERE bot_id = $1 AND status IN ('completed', 'confirmed')
              AND created_at >= $2 AND created_at <= $3
            """,
            bot_uuid,
            period_start,
            period_end
        )

        # Get daily revenue data
        rows = await db.fetch(
            """
            SELECT
                DATE(created_at) as date,
                COALESCE(SUM(price), 0) as revenue,
                COUNT(*) as appointments
            FROM appointments
            WHERE bot_id = $1 AND status IN ('completed', 'confirmed')
              AND created_at >= $2 AND created_at <= $3
            GROUP BY DATE(created_at)
            ORDER BY date ASC
            """,
            bot_uuid,
            period_start,
            period_end
        )

        daily_data = [
            RevenueDataPoint(
                date=str(row['date']),
                revenue=float(row['revenue']),
                appointments=row['appointments']
            )
            for row in rows
        ]

        return RevenueResponse(
            bot_id=str(bot_uuid),
            bot_name=bot['bot_name'],
            total_revenue=float(total_revenue),
            period_revenue=float(period_revenue),
            period_appointments=period_appointments,
            period_start=period_start,
            period_end=period_end,
            daily_data=daily_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bot revenue: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/bots/{bot_id}/appointments", response_model=AppointmentsStats)
async def get_bot_appointments_stats(
    bot_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Database = Depends(get_database),
    current_master: dict = Depends(get_current_master)
) -> AppointmentsStats:
    """
    Get appointments statistics for a specific bot

    Args:
        bot_id: Bot UUID
        days: Number of days to analyze (1-365)

    Returns:
        Appointments statistics
    """
    try:
        bot_uuid = uuid.UUID(bot_id)

        # Verify bot ownership
        bot = await db.fetchrow(
            "SELECT id, bot_name FROM bots WHERE id = $1 AND master_id = $2",
            bot_uuid,
            current_master['id']
        )

        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")

        period_start = datetime.now() - timedelta(days=days)

        # Get total appointments
        total = await db.fetchval(
            """
            SELECT COUNT(*)
            FROM appointments
            WHERE bot_id = $1 AND created_at >= $2
            """,
            bot_uuid,
            period_start
        )

        # Get counts by status
        rows = await db.fetch(
            """
            SELECT status, COUNT(*) as count
            FROM appointments
            WHERE bot_id = $1 AND created_at >= $2
            GROUP BY status
            """,
            bot_uuid,
            period_start
        )

        status_counts = {row['status']: row['count'] for row in rows}

        pending = status_counts.get('pending', 0)
        confirmed = status_counts.get('confirmed', 0)
        completed = status_counts.get('completed', 0)
        cancelled = status_counts.get('cancelled', 0)

        # Calculate conversion rate (confirmed / total)
        conversion_rate = (confirmed / total * 100) if total > 0 else 0.0

        return AppointmentsStats(
            bot_id=str(bot_uuid),
            bot_name=bot['bot_name'],
            total=total,
            pending=pending,
            confirmed=confirmed,
            completed=completed,
            cancelled=cancelled,
            conversion_rate=round(conversion_rate, 2)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bot appointments stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================
# Master Analytics Endpoints
# ============================================

@router.get("/masters/overview", response_model=MasterOverviewResponse)
async def get_master_overview(
    db: Database = Depends(get_database),
    current_master: dict = Depends(get_current_master)
) -> MasterOverviewResponse:
    """
    Get overview statistics for the current master

    Returns:
        Master overview statistics
    """
    try:
        master_id = current_master['id']

        # Get total bots
        total_bots = await db.fetchval(
            "SELECT COUNT(*) FROM bots WHERE master_id = $1",
            master_id
        )

        # Get active bots
        active_bots = await db.fetchval(
            "SELECT COUNT(*) FROM bots WHERE master_id = $1 AND is_active = true",
            master_id
        )

        # Get total appointments across all bots
        total_appointments = await db.fetchval(
            """
            SELECT COUNT(*)
            FROM appointments a
            JOIN bots b ON b.id = a.bot_id
            WHERE b.master_id = $1
            """,
            master_id
        )

        # Get total revenue across all bots
        total_revenue = await db.fetchval(
            """
            SELECT COALESCE(SUM(a.price), 0)
            FROM appointments a
            JOIN bots b ON b.id = a.bot_id
            WHERE b.master_id = $1 AND a.status IN ('completed', 'confirmed')
            """,
            master_id
        ) or 0.0

        # Get unique clients across all bots
        unique_clients = await db.fetchval(
            """
            SELECT COUNT(DISTINCT c.id)
            FROM clients c
            JOIN bots b ON b.id = c.bot_id
            WHERE b.master_id = $1
            """,
            master_id
        )

        return MasterOverviewResponse(
            master_id=str(master_id),
            total_bots=total_bots,
            active_bots=active_bots,
            total_appointments=total_appointments,
            total_revenue=float(total_revenue),
            unique_clients=unique_clients
        )

    except Exception as e:
        logger.error(f"Error getting master overview: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================
# Event Logging Endpoint
# ============================================

@router.post("/events")
async def log_analytics_event(
    event: LogEventRequest,
    db: Database = Depends(get_database),
    current_master: dict = Depends(get_current_master)
) -> dict:
    """
    Log analytics event

    Args:
        event: Event data

    Returns:
        Success message
    """
    try:
        bot_uuid = None
        if event.bot_id:
            bot_uuid = uuid.UUID(event.bot_id)
            # Verify bot ownership
            bot = await db.fetchrow(
                "SELECT id FROM bots WHERE id = $1 AND master_id = $2",
                bot_uuid,
                current_master['id']
            )
            if not bot:
                raise HTTPException(status_code=404, detail="Bot not found")
        await db.execute(
            """
            INSERT INTO analytics_events (bot_id, event_type, user_id, event_data)
            VALUES ($1, $2, $3, $4)
            """,
            bot_uuid,
            event.event_type,
            event.user_id,
            event.event_data or {}
        )

        logger.info(f"Analytics event logged: {event.event_type}")

        return {"status": "success", "message": "Event logged successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging analytics event: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
