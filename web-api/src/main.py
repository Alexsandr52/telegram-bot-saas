"""
Web API - Main Entry Point
FastAPI application for web panel
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys

from src.utils.config import get_settings
from src.utils.db import init_database, close_database

# Import routers
from src.api import auth, bots, services, schedules, appointments


# ============================================
# Configuration
# ============================================

settings = get_settings()

# Configure logger
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.LOG_LEVEL
)


# ============================================
# Database
# ============================================

_db = None


async def init_db():
    """Initialize database connection"""
    global _db
    _db = await init_database(settings.DATABASE_URL)
    logger.info("Database initialized")


def get_db():
    """Get database instance"""
    return _db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager"""
    # Startup
    await init_db()
    logger.info("Web API starting up...")
    yield
    # Shutdown
    await close_database()
    logger.info("Web API shutting down...")


# ============================================
# FastAPI App
# ============================================

app = FastAPI(
    title="Telegram Bot SaaS - Web API",
    description="API for web panel",
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(bots.router, prefix=settings.API_PREFIX)
app.include_router(services.router, prefix=settings.API_PREFIX)
app.include_router(schedules.router, prefix=settings.API_PREFIX)
app.include_router(appointments.router, prefix=settings.API_PREFIX)


# ============================================
# Health Check
# ============================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Telegram Bot SaaS Web API",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


# ============================================
# Main
# ============================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
