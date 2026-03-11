"""
Bot management API endpoints
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional
from loguru import logger

router = APIRouter()


# ============================================
# Request/Response Models
# ============================================

class CreateBotRequest(BaseModel):
    """Request to create a new bot container"""
    bot_id: str = Field(..., description="Bot UUID from database")
    bot_token: str = Field(..., description="Telegram bot token")
    bot_username: str = Field(..., description="Bot username")
    webhook_url: Optional[str] = Field(None, description="Webhook URL")


class BotResponse(BaseModel):
    """Response with bot information"""
    bot_id: str
    container_id: str
    status: str
    message: str


class ContainerStatus(BaseModel):
    """Container status information"""
    container_id: str
    status: str
    running: bool
    restart_count: int


# ============================================
# Endpoints
# ============================================

@router.post("/bots/", response_model=BotResponse)
async def create_bot_container(
    request: CreateBotRequest,
    background_tasks: BackgroundTasks
):
    """
    Create a new Docker container for a bot

    This endpoint:
    1. Creates a new Docker container from bot-template image
    2. Configures environment variables (BOT_ID, BOT_TOKEN, DATABASE_URL)
    3. Sets up webhook if provided
    4. Starts the container
    """
    try:
        # Import Docker manager
        import main
        docker_manager = main.docker_manager

        logger.info(f"Creating container for bot {request.bot_id} (@{request.bot_username})")

        # Create container
        container_id = await docker_manager.create_bot_container(
            bot_id=request.bot_id,
            bot_token=request.bot_token,
            webhook_url=request.webhook_url
        )

        return BotResponse(
            bot_id=request.bot_id,
            container_id=container_id,
            status="creating",
            message="Bot container created successfully"
        )

    except Exception as e:
        logger.error(f"Error creating bot container: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bots/{bot_id}/status", response_model=ContainerStatus)
async def get_bot_status(bot_id: str):
    """Get status of a bot container"""
    try:
        import main
        docker_manager = main.docker_manager

        container = await docker_manager.get_container(bot_id)
        if not container:
            raise HTTPException(status_code=404, detail="Bot container not found")

        status = await docker_manager.get_container_status(bot_id)

        return ContainerStatus(
            container_id=container['Id'],
            status=status,
            running=status == "running",
            restart_count=container.get('RestartCount', 0)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bot status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bots/{bot_id}/start")
async def start_bot(bot_id: str):
    """Start a bot container"""
    try:
        import main
        docker_manager = main.docker_manager

        logger.info(f"Starting bot {bot_id}")
        await docker_manager.start_container(bot_id)

        return {"bot_id": bot_id, "status": "started", "message": "Bot started successfully"}

    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bots/{bot_id}/stop")
async def stop_bot(bot_id: str):
    """Stop a bot container"""
    try:
        import main
        docker_manager = main.docker_manager

        logger.info(f"Stopping bot {bot_id}")
        await docker_manager.stop_container(bot_id)

        return {"bot_id": bot_id, "status": "stopped", "message": "Bot stopped successfully"}

    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bots/{bot_id}/restart")
async def restart_bot(bot_id: str):
    """Restart a bot container"""
    try:
        import main
        docker_manager = main.docker_manager

        logger.info(f"Restarting bot {bot_id}")
        await docker_manager.restart_container(bot_id)

        return {"bot_id": bot_id, "status": "restarted", "message": "Bot restarted successfully"}

    except Exception as e:
        logger.error(f"Error restarting bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/bots/{bot_id}")
async def delete_bot(bot_id: str):
    """
    Delete a bot container

    WARNING: This will permanently remove the container and all its data
    """
    try:
        import main
        docker_manager = main.docker_manager

        logger.warning(f"Deleting bot {bot_id}")
        await docker_manager.delete_container(bot_id)

        return {"bot_id": bot_id, "status": "deleted", "message": "Bot deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bots")
async def list_bots():
    """List all bot containers"""
    try:
        import main
        docker_manager = main.docker_manager

        containers = await docker_manager.list_bot_containers()

        # Parse labels from string format
        def parse_label(labels_str: str, key: str) -> str:
            """Parse a label value from comma-separated labels string"""
            if not labels_str:
                return None
            for label in labels_str.split(','):
                if '=' in label:
                    k, v = label.split('=', 1)
                    if k.strip() == key:
                        return v.strip()
            return None

        return {
            "count": len(containers),
            "containers": [
                {
                    "bot_id": parse_label(c.get('Labels', ''), 'bot_id'),
                    "container_id": c.get('ID'),
                    "status": c.get('State'),
                    "name": c.get('Names')
                }
                for c in containers
            ]
        }

    except Exception as e:
        logger.error(f"Error listing bots: {e}")
        raise HTTPException(status_code=500, detail=str(e))
