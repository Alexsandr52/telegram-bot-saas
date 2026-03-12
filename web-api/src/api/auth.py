"""
Auth API endpoints
Handles login/logout and session management
"""
from fastapi import APIRouter, HTTPException, Depends, status
from loguru import logger

from ..models import LoginRequest, LoginResponse, ErrorResponse
from ..utils.db import SessionRepository

router = APIRouter(prefix="/auth", tags=["auth"])


# Dependency to get repositories
def get_repositories(db):
    """Get repository instances"""
    return {
        'session': SessionRepository(db)
    }


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db=Depends(lambda: None)  # Will be properly injected
):
    """
    Login with token from Platform Bot

    Token is a one-time code generated in the bot
    """
    # TODO: Implement proper dependency injection
    from ..main import get_db
    db_instance = get_db()

    session_repo = SessionRepository(db_instance)

    try:
        # Get session by token
        session = await session_repo.get_session(request.token)

        if not session:
            return LoginResponse(
                success=False,
                message="Неверный или истекший код. Получите новый код в боте."
            )

        # Update session activity
        await session_repo.update_session_activity(request.token)

        logger.info(f"User logged in: {session['master_id']}")

        return LoginResponse(
            success=True,
            message="Успешный вход",
            master_id=str(session['master_id'])
        )

    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/logout")
async def logout(
    token: str,
    db=Depends(lambda: None)
):
    """Logout and invalidate session"""
    from ..main import get_db
    db_instance = get_db()

    session_repo = SessionRepository(db_instance)

    try:
        await session_repo.delete_session(token)
        return {"success": True, "message": "Logged out successfully"}

    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
