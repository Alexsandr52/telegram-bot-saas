"""
Platform Bot Metrics
Prometheus metrics export for monitoring
"""
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from functools import wraps
from time import time
import logging

logger = logging.getLogger(__name__)

# ============================================
# Counters
# ============================================

# Message metrics
messages_sent_total = Counter(
    'bot_messages_sent_total',
    'Total messages sent by the bot',
    ['bot_id', 'message_type']
)

messages_received_total = Counter(
    'bot_messages_received_total',
    'Total messages received by the bot',
    ['bot_id', 'message_type']
)

# Error metrics
errors_total = Counter(
    'bot_errors_total',
    'Total errors encountered',
    ['bot_id', 'error_type', 'error_level']
)

# User metrics
users_active = Gauge(
    'bot_active_users',
    'Number of active users',
    ['bot_id']
)

users_new = Counter(
    'bot_new_users_total',
    'Total new users',
    ['bot_id']
)

# Database metrics
db_queries_total = Counter(
    'database_queries_total',
    'Total database queries',
    ['query_type', 'table']
)

db_connections_active = Gauge(
    'database_connections_active',
    'Active database connections',
    ['database']
)

# ============================================
# Histograms
# ============================================

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint', 'status_code']
)

bot_action_duration = Histogram(
    'bot_action_duration_seconds',
    'Bot action duration',
    ['bot_id', 'action_type']
)

db_query_duration = Histogram(
    'database_query_duration_seconds',
    'Database query duration',
    ['query_type', 'table']
)

# ============================================
# Decorators
# ============================================

def track_request(method: str = "", endpoint: str = ""):
    """Decorator to track HTTP request duration"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time()
            try:
                result = await func(*args, **kwargs)
                status_code = getattr(result, 'status_code', 200)
                duration = time() - start_time

                request_duration.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code
                ).observe(duration)

                return result
            except Exception as e:
                duration = time() - start_time
                status_code = getattr(e, 'status_code', 500)

                request_duration.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code
                ).observe(duration)

                errors_total.labels(
                    bot_id='platform-bot',
                    error_type=type(e).__name__,
                    error_level='ERROR'
                ).inc()

                raise
        return wrapper
    return decorator

def track_bot_action(bot_id: str = "platform-bot", action_type: str = "action"):
    """Decorator to track bot action duration"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time()
            try:
                result = await func(*args, **kwargs)
                duration = time() - start_time

                bot_action_duration.labels(
                    bot_id=bot_id,
                    action_type=action_type
                ).observe(duration)

                return result
            except Exception as e:
                duration = time() - start_time

                bot_action_duration.labels(
                    bot_id=bot_id,
                    action_type=action_type
                ).observe(duration)

                errors_total.labels(
                    bot_id=bot_id,
                    error_type=type(e).__name__,
                    error_level='ERROR'
                ).inc()

                raise
        return wrapper
    return decorator

# ============================================
# Metrics Server
# ============================================

def start_metrics_server(port: int = 9090):
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
        "service": "platform-bot-metrics",
        "metrics_endpoint": f"/metrics"
    }
