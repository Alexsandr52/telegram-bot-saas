"""
Logging Service - Main Entry Point
FastAPI application for centralized log management
"""
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import setup_logging
from api import router as logs_router


# Get environment variables
APP_NAME = "logging-service"
APP_VERSION = "1.0.0"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8001"))

# CORS origins
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:80"
).split(",")

# Setup logger
logger = setup_logging(
    service_name=APP_NAME,
    level=os.getenv("LOG_LEVEL", "INFO"),
    log_format=os.getenv("LOG_FORMAT", "json"),
    log_file=os.getenv("LOG_FILE_PATH", "/var/log/logging/app.log"),
    console_output=True,
    log_to_db=True,
    sentry_dsn=os.getenv("SENTRY_DSN")
)

logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
logger.info(f"Listening on {HOST}:{PORT}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager"""
    # Startup
    logger.info(f"{APP_NAME} startup")
    logger.info("Database connection initializing")

    yield

    # Shutdown
    logger.info(f"{APP_NAME} shutdown")


# Create FastAPI app
app = FastAPI(
    title="Telegram Bot SaaS - Logging Service",
    description="Centralized log management API",
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(logs_router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": APP_NAME,
        "version": APP_VERSION,
        "status": "running",
        "endpoints": {
            "logs": "/api/v1/logs",
            "stats": "/api/v1/logs/stats",
            "export": "/api/v1/logs/export",
            "cleanup": "/api/v1/logs/cleanup",
            "services": "/api/v1/logs/services",
            "levels": "/api/v1/logs/levels"
        },
        "docs": "/docs"
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": APP_NAME,
        "version": APP_VERSION,
        "timestamp": logger._create_log_entry(
            logger.level,
            "Health check passed",
            service=APP_NAME,
            function="health_check",
            line_num=76
        )
    }


def main():
    """Main entry point"""
    import uvicorn

    logger.info(f"Starting Uvicorn server on {HOST}:{PORT}")

    uvicorn.run(
        f"{APP_NAME}:app",
        host=HOST,
        port=PORT,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()
