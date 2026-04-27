"""
Factory Service Metrics
Prometheus metrics export for container management
"""
from prometheus_client import Counter, Gauge, start_http_server
from functools import wraps
from time import time
import logging

logger = logging.getLogger(__name__)

# ============================================
# Container Metrics
# ============================================

containers_running = Gauge(
    'factory_containers_running',
    'Number of running bot containers',
    ['service']
)

containers_stopped = Gauge(
    'factory_containers_stopped',
    'Number of stopped bot containers',
    ['service']
)

containers_created_total = Counter(
    'factory_containers_created_total',
    'Total containers created',
    ['service', 'status']
)

containers_stopped_total = Counter(
    'factory_containers_stopped_total',
    'Total containers stopped',
    ['service', 'reason']
)

# ============================================
# Docker Metrics
# ============================================

docker_operations_total = Counter(
    'factory_docker_operations_total',
    'Total Docker operations',
    ['operation_type', 'status']
)

docker_operation_duration = Histogram(
    'factory_docker_operation_duration_seconds',
    'Docker operation duration',
    ['operation_type']
)

# ============================================
# API Metrics
# ============================================

api_requests_total = Counter(
    'factory_api_requests_total',
    'Total API requests',
    ['endpoint', 'method']
)

api_requests_failed = Counter(
    'factory_api_requests_failed',
    'Failed API requests',
    ['endpoint', 'method', 'error_type']
)

api_request_duration = Histogram(
    'factory_api_request_duration_seconds',
    'API request duration',
    ['endpoint', 'method']
)

# ============================================
# Resource Metrics
# ============================================

docker_disk_usage = Gauge(
    'factory_docker_disk_usage_bytes',
    'Docker disk usage in bytes'
)

docker_memory_usage = Gauge(
    'factory_docker_memory_usage_bytes',
    'Docker memory usage in bytes'
)

# ============================================
# Decorators
# ============================================

def track_docker_operation(operation_type: str = "operation"):
    """Decorator to track Docker operation duration"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time()
            try:
                result = await func(*args, **kwargs)
                duration = time() - start_time

                docker_operation_duration.labels(
                    operation_type=operation_type
                ).observe(duration)

                docker_operations_total.labels(
                    operation_type=operation_type,
                    status='success'
                ).inc()

                return result
            except Exception as e:
                duration = time() - start_time

                docker_operation_duration.labels(
                    operation_type=operation_type
                ).observe(duration)

                docker_operations_total.labels(
                    operation_type=operation_type,
                    status='failed'
                ).inc()

                raise
        return wrapper
    return decorator

def track_api_request(endpoint: str = "", method: str = ""):
    """Decorator to track API request duration"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time()
            try:
                result = await func(*args, **kwargs)
                duration = time() - start_time

                api_request_duration.labels(
                    endpoint=endpoint,
                    method=method
                ).observe(duration)

                api_requests_total.labels(
                    endpoint=endpoint,
                    method=method
                ).inc()

                return result
            except Exception as e:
                duration = time() - start_time

                api_request_duration.labels(
                    endpoint=endpoint,
                    method=method
                ).observe(duration)

                api_requests_failed.labels(
                    endpoint=endpoint,
                    method=method,
                    error_type=type(e).__name__
                ).inc()

                raise
        return wrapper
    return decorator

# ============================================
# Metrics Server
# ============================================

def start_metrics_server(port: int = 9091):
    """Start Prometheus metrics server"""
    try:
        start_http_server(port)
        logger.info(f"Prometheus metrics server started on port {port}")
        logger.info(f"Metrics available at http://localhost:{port}/metrics")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")
        raise

# ============================================
# Health Check for Metrics
# ============================================

def metrics_health():
    """Health check for metrics endpoint"""
    return {
        "status": "healthy",
        "service": "factory-service-metrics",
        "metrics_endpoint": f"/metrics"
    }
