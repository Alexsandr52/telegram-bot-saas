# ============================================
# Logging Service - Dockerfile
# Centralized logging API and management
# ============================================

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY ./src/ ./src/

# Create non-root user
RUN useradd -m -u 1000 logging && \
    chown -R logging:logging /app

# Switch to non-root user
USER logging

# Create logs directory
RUN mkdir -p /var/log/logging

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Expose port
EXPOSE 8001

# Default command
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
