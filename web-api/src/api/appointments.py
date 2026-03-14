"""
Appointments API endpoints
Handles appointment management
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query
from loguru import logger
import uuid

from ..models import (
    AppointmentResponse,
    AppointmentsListResponse,
    AppointmentStatusUpdate,
    ErrorResponse
)
from ..utils.db import AppointmentRepository, SessionRepository, BotRepository

router = APIRouter(prefix="/appointments", tags=["appointments"])


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


@router.get("/{bot_id}", response_model=AppointmentsListResponse)
async def get_appointments(
    bot_id: str,
    token: str,
    status_filter: str = Query(None, description="Filter by status (pending, confirmed, completed, cancelled)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db=Depends(lambda: None)
):
    """Get appointments for a bot"""
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

        appointment_repo = AppointmentRepository(db_instance)
        appointments = await appointment_repo.get_bot_appointments(
            uuid.UUID(bot_id),
            limit=limit,
            offset=offset,
            status_filter=status_filter
        )

        return AppointmentsListResponse(
            appointments=[
                AppointmentResponse(
                    id=str(appt['id']),
                    start_time=appt['start_time'],
                    end_time=appt['end_time'],
                    status=appt['status'],
                    price=float(appt['price']) if appt.get('price') else 0.0,
                    client_first_name=appt.get('first_name'),
                    client_last_name=appt.get('last_name'),
                    client_phone=appt.get('phone'),
                    service_name=appt['service_name']
                )
                for appt in appointments
            ],
            total=len(appointments)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting appointments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put("/{appointment_id}/status", response_model=AppointmentResponse)
async def update_appointment_status(
    appointment_id: str,
    status_update: AppointmentStatusUpdate,
    token: str,
    db=Depends(lambda: None)
):
    """Update appointment status"""
    from ..main import get_db
    db_instance = get_db()

    try:
        master_id = await get_master_id_from_token(token, db_instance)

        appointment_repo = AppointmentRepository(db_instance)

        # First get the appointment to verify it exists and belongs to master's bot
        appt = await appointment_repo.get_appointment_by_id(uuid.UUID(appointment_id))
        if not appt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )

        # Verify bot ownership
        if not await verify_bot_ownership(str(appt['bot_id']), master_id, db_instance):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        # Update status
        await appointment_repo.update_appointment_status(
            uuid.UUID(appointment_id),
            status_update.status
        )

        # Get updated appointment with client info
        updated_appt = await appointment_repo.get_appointment_by_id(uuid.UUID(appointment_id))
        if not updated_appt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found after update"
            )

        return AppointmentResponse(
            id=str(updated_appt['id']),
            start_time=updated_appt['start_time'],
            end_time=updated_appt['end_time'],
            status=updated_appt['status'],
            price=float(updated_appt['price']) if updated_appt.get('price') else 0.0,
            client_first_name=updated_appt.get('first_name'),
            client_last_name=updated_appt.get('last_name'),
            client_phone=updated_appt.get('phone'),
            service_name=updated_appt['service_name']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating appointment status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
