"""
Factory Service - Main Entry Point
Manages Docker containers for bot instances
"""
import asyncio
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.bots import router as bots_router
from api.health import router as health_router
from docker.manager import DockerManager


# Global Docker manager instance
docker_manager: DockerManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager"""
    global docker_manager

    # Startup
    logger.info("Starting Factory Service...")

    # Initialize Docker manager
    docker_manager = DockerManager()
    await docker_manager.initialize()

    # Store in app state for access in endpoints
    app.state.docker_manager = docker_manager

    logger.info("Factory Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Factory Service...")
    await docker_manager.close()
    logger.info("Factory Service stopped")


# Create FastAPI app
app = FastAPI(
    title="Factory Service",
    description="Manages Docker containers for Telegram bot instances",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
allowed_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix="/api/v1", tags=["health"])
app.include_router(bots_router, prefix="/api/v1/factory", tags=["bots"])


# ============================================
# Main
# ============================================

def main():
    """Run the application"""
    import uvicorn

    # Configure logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
        level=os.getenv("LOG_LEVEL", "INFO")
    )

    # Get config
    host = os.getenv("FACTORY_HOST", "0.0.0.0")
    port = int(os.getenv("FACTORY_PORT", "8001"))

    logger.info(f"Starting Factory Service on {host}:{port}")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("DEBUG", "false").lower() == "true",
        log_level="info"
    )


if __name__ == "__main__":
    main()
