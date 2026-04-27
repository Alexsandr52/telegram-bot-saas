FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Docker CLI
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    docker-cli \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/

# Expose port
EXPOSE 8002

# Health check - check if the API is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8002/api/v1/health || exit 1

# Run application
# Note: Running as root to access Docker socket
# In production, consider using Docker SDK with proper socket permissions
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8002"]
