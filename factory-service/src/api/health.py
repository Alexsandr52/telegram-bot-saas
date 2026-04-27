"""
Health check endpoints
"""
from fastapi import APIRouter, Request
from datetime import datetime

router = APIRouter()


@router.get("/health")
async def health_check(request: Request):
    """Health check endpoint with Docker connectivity check"""
    from fastapi import Request as FastAPIRequest
    from docker.manager import DockerManager

    health_status = {
        "status": "healthy",
        "service": "factory-service",
        "timestamp": datetime.utcnow().isoformat()
    }

    # Check Docker connectivity
    try:
        # This is a basic check - actual Docker connectivity is checked in the manager
        # We'll just verify the manager is accessible
        docker_client = DockerManager()
        await docker_client.initialize()
        await docker_client.close()
        health_status["docker"] = "connected"
    except Exception as e:
        health_status["docker"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"

    return health_status


@router.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Factory Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/api/v1/health",
            "bots": "/api/v1/factory/bots",
            "containers": "/api/v1/factory/containers"
        }
    }
