#!/bin/bash
# ============================================
# Test Production Configuration Locally
# ============================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Testing Production Configuration Locally${NC}"
echo "=========================================="
echo

# Check if .env.prod exists
if [ ! -f ".env.prod" ]; then
    echo "❌ .env.prod file not found!"
    echo "Please copy .env.prod.example to .env.prod and configure it."
    exit 1
fi

# Source the env file
export $(cat .env.prod | grep -v '^#' | xargs)

# Validate required variables
REQUIRED_VARS=(
    "SERVER_DOMAIN"
    "WEBHOOK_BASE_URL"
    "POSTGRES_PASSWORD"
    "REDIS_PASSWORD"
    "ENCRYPTION_KEY"
    "JWT_SECRET_KEY"
    "PLATFORM_BOT_TOKEN"
)

MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ] || [[ "${!var}" == *"CHANGE_THIS"* ]]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo "❌ Missing or unconfigured variables:"
    for var in "${MISSING_VARS[@]}"; do
        echo "   - $var"
    done
    echo
    echo "Please configure these variables in .env.prod"
    exit 1
fi

echo -e "${GREEN}✓ Environment variables validated${NC}"
echo

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed"
    exit 1
fi

echo -e "${GREEN}✓ Docker and Docker Compose installed${NC}"
echo

# Create necessary directories
echo "Creating directories..."
mkdir -p certbot/conf certbot/www
mkdir -p backups/postgres bot-templates
mkdir -p logs/{api,factory,notifications,central}
echo -e "${GREEN}✓ Directories created${NC}"
echo

# Test Docker Compose configuration
echo "Testing Docker Compose configuration..."
docker-compose -f docker-compose.prod.yml config > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Docker Compose configuration is valid${NC}"
else
    echo "❌ Docker Compose configuration has errors"
    exit 1
fi
echo

# Check nginx configuration
echo "Testing nginx configuration..."
if [ -f "nginx/nginx-prod.conf" ]; then
    # Try to validate with a temporary docker container
    docker run --rm -v $(pwd)/nginx/nginx-prod.conf:/etc/nginx/nginx.conf:ro nginx:alpine nginx -t 2>&1 | grep -q "syntax is ok"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
    else
        echo "⚠️  Nginx configuration may have issues (SSL certs not present)"
    fi
else
    echo "❌ nginx/nginx-prod.conf not found"
    exit 1
fi
echo

# Build images
echo "Building Docker images (this may take a while)..."
docker-compose -f docker-compose.prod.yml build --no-cache
echo -e "${GREEN}✓ Docker images built successfully${NC}"
echo

echo "=========================================="
echo -e "${GREEN}✓ All tests passed!${NC}"
echo
echo "You can now:"
echo "  1. Test locally: docker-compose -f docker-compose.prod.yml up"
echo "  2. Deploy to VPS: ./scripts/deploy-to-vps.sh"
echo
echo "Note: For local testing, use localhost as SERVER_DOMAIN"
echo "      and set NGROK_ENABLED=true to test webhooks"
