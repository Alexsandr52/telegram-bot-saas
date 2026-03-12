"""
Schedules API endpoints
Handles schedule management
"""
from fastapi import APIRouter, HTTPException, Depends, status
from loguru import logger
import uuid

from ..models import ScheduleItem, ScheduleUpdate, ScheduleResponse, ErrorResponse
from ..utils.db import ScheduleRepository, SessionRepository, BotRepository

router = APIRouter(prefix="/schedules", tags=["schedules"])


async def get_master_id_from_token(token: str, db) -> str:
    """Get master_id from session token"""
    session_repo = SessionRepository(db)
    session = await session_repo.get_session(token)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    return str(session['master_id'])


async def verify_bot_ownership(bot_id: str, master_id: str, db) -> bool:
    """Verify that the bot belongs to the master"""
    bot_repo = BotRepository(db)
    bot = await bot_repo.get_bot_by_id(uuid.UUID(bot_id))

    if not bot:
        return False

    return str(bot['master_id']) == master_id


@router.get("/{bot_id}", response_model=ScheduleResponse)
async def get_schedule(
    bot_id: str,
    token: str,
    db=Depends(lambda: None)
):
    """Get schedule for a bot"""
    from ..main import get_db
    db_instance = get_db()

    try:
        master_id = await get_master_id_from_token(token, db_instance)

        # Verify ownership
        if not await verify_bot_ownership(bot_id, master_id, db_instance):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        schedule_repo = ScheduleRepository(db_instance)
        schedules = await schedule_repo.get_bot_schedules(uuid.UUID(bot_id))

        return ScheduleResponse(
            schedules=[
                ScheduleItem(
                    day_of_week=s['day_of_week'],
                    start_time=str(s['start_time']),
                    end_time=str(s['end_time']),
                    is_working_day=s['is_working_day'],
                    break_start_time=str(s['break_start_time']) if s.get('break_start_time') else None,
                    break_end_time=str(s['break_end_time']) if s.get('break_end_time') else None
                )
                for s in schedules
            ]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put("/{bot_id}", response_model=ScheduleResponse)
async def update_schedule(
    bot_id: str,
    schedule_data: ScheduleUpdate,
    token: str,
    db=Depends(lambda: None)
):
    """Update schedule for a bot"""
    from ..main import get_db
    db_instance = get_db()

    try:
        master_id = await get_master_id_from_token(token, db_instance)

        # Verify ownership
        if not await verify_bot_ownership(bot_id, master_id, db_instance):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        schedule_repo = ScheduleRepository(db_instance)

        # Update each day's schedule
        for schedule_item in schedule_data.schedules:
            await schedule_repo.set_schedule(
                bot_id=uuid.UUID(bot_id),
                day_of_week=schedule_item.day_of_week,
                start_time=schedule_item.start_time,
                end_time=schedule_item.end_time,
                is_working_day=schedule_item.is_working_day,
                break_start_time=schedule_item.break_start_time,
                break_end_time=schedule_item.break_end_time
            )

        # Get updated schedule
        schedules = await schedule_repo.get_bot_schedules(uuid.UUID(bot_id))

        return ScheduleResponse(
            schedules=[
                ScheduleItem(
                    day_of_week=s['day_of_week'],
                    start_time=str(s['start_time']),
                    end_time=str(s['end_time']),
                    is_working_day=s['is_working_day'],
                    break_start_time=str(s['break_start_time']) if s.get('break_start_time') else None,
                    break_end_time=str(s['break_end_time']) if s.get('break_end_time') else None
                )
                for s in schedules
            ]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
