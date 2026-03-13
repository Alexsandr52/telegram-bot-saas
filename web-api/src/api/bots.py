"""
Bots API endpoints
Handles bot management
"""
from fastapi import APIRouter, HTTPException, Depends, status
from loguru import logger

from ..models import BotsListResponse, BotResponse, ErrorResponse
from ..utils.db import BotRepository, MasterRepository, SessionRepository

router = APIRouter(prefix="/bots", tags=["bots"])


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


@router.get("", response_model=BotsListResponse)
async def get_bots(
    token: str,
    db=Depends(lambda: None)
):
    """Get all bots for the authenticated master"""
    from ..main import get_db
    db_instance = get_db()

    try:
        master_id = await get_master_id_from_token(token, db_instance)

        # Convert string to UUID
        import uuid
        master_repo = MasterRepository(db_instance)
        bots = await master_repo.get_master_bots(uuid.UUID(master_id))

        return BotsListResponse(
            bots=[
                BotResponse(
                    id=str(bot['id']),
                    bot_username=bot['bot_username'],
                    bot_name=bot.get('bot_name'),
                    business_name=bot.get('business_name'),
                    container_status=bot['container_status'],
                    is_active=bot['is_active']
                )
                for bot in bots
            ]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bots: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{bot_id}", response_model=BotResponse)
async def get_bot(
    bot_id: str,
    token: str,
    db=Depends(lambda: None)
):
    """Get bot details"""
    from ..main import get_db
    db_instance = get_db()

    try:
        master_id = await get_master_id_from_token(token, db_instance)

        bot_repo = BotRepository(db_instance)
        import uuid
        bot = await bot_repo.get_bot_by_id(uuid.UUID(bot_id))

        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot not found"
            )

        # Verify ownership
        if str(bot['master_id']) != master_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        return BotResponse(
            id=str(bot['id']),
            bot_username=bot['bot_username'],
            bot_name=bot.get('bot_name'),
            business_name=bot.get('business_name'),
            container_status=bot['container_status'],
            is_active=bot['is_active']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
