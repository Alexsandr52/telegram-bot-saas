"""
Services API endpoints
Handles service management
"""
from fastapi import APIRouter, HTTPException, Depends, status
from loguru import logger
import uuid

from ..models import (
    ServiceCreate,
    ServiceUpdate,
    ServiceResponse,
    ServicesListResponse,
    ErrorResponse
)
from ..utils.db import ServiceRepository, SessionRepository, BotRepository

router = APIRouter(prefix="/services", tags=["services"])


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


@router.get("/{bot_id}", response_model=ServicesListResponse)
async def get_services(
    bot_id: str,
    token: str,
    db=Depends(lambda: None)
):
    """Get all services for a bot"""
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

        service_repo = ServiceRepository(db_instance)
        services = await service_repo.get_bot_services(uuid.UUID(bot_id))

        return ServicesListResponse(
            services=[
                ServiceResponse(
                    id=str(service['id']),
                    name=service['name'],
                    description=service.get('description'),
                    price=float(service['price']),
                    duration_minutes=service['duration_minutes'],
                    is_active=service['is_active'],
                    sort_order=service['sort_order']
                )
                for service in services
            ]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting services: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/{bot_id}", response_model=ServiceResponse)
async def create_service(
    bot_id: str,
    service: ServiceCreate,
    token: str,
    db=Depends(lambda: None)
):
    """Create a new service"""
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

        service_repo = ServiceRepository(db_instance)
        service_id = await service_repo.create_service(
            bot_id=uuid.UUID(bot_id),
            name=service.name,
            description=service.description,
            price=service.price,
            duration_minutes=service.duration_minutes,
            sort_order=service.sort_order
        )

        # Get the created service
        services = await service_repo.get_bot_services(uuid.UUID(bot_id))
        created_service = next((s for s in services if str(s['id']) == str(service_id)), None)

        if not created_service:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create service"
            )

        return ServiceResponse(
            id=str(created_service['id']),
            name=created_service['name'],
            description=created_service.get('description'),
            price=float(created_service['price']),
            duration_minutes=created_service['duration_minutes'],
            is_active=created_service['is_active'],
            sort_order=created_service['sort_order']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: str,
    service: ServiceUpdate,
    token: str,
    db=Depends(lambda: None)
):
    """Update a service"""
    from ..main import get_db
    db_instance = get_db()

    try:
        master_id = await get_master_id_from_token(token, db_instance)

        service_repo = ServiceRepository(db_instance)

        # Get service first to verify ownership
        services = await service_repo.get_bot_services(uuid.UUID(service_id))
        if not services:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found"
            )

        await service_repo.update_service(
            uuid.UUID(service_id),
            name=service.name,
            description=service.description,
            price=service.price,
            duration_minutes=service.duration_minutes,
            is_active=service.is_active,
            sort_order=service.sort_order
        )

        # Get updated service
        services = await service_repo.get_bot_services(uuid.UUID(service_id))
        updated_service = next((s for s in services if str(s['id']) == service_id), None)

        return ServiceResponse(
            id=str(updated_service['id']),
            name=updated_service['name'],
            description=updated_service.get('description'),
            price=float(updated_service['price']),
            duration_minutes=updated_service['duration_minutes'],
            is_active=updated_service['is_active'],
            sort_order=updated_service['sort_order']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete("/{service_id}")
async def delete_service(
    service_id: str,
    token: str,
    db=Depends(lambda: None)
):
    """Delete a service (soft delete)"""
    from ..main import get_db
    db_instance = get_db()

    try:
        master_id = await get_master_id_from_token(token, db_instance)

        service_repo = ServiceRepository(db_instance)
        await service_repo.delete_service(uuid.UUID(service_id))

        return {"success": True, "message": "Service deleted"}

    except Exception as e:
        logger.error(f"Error deleting service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
