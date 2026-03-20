#!/bin/bash
# ============================================
# Check Production Readiness
# Verifies all requirements for VPS deployment
# ============================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

total_checks=0
passed_checks=0
failed_checks=0

check() {
    local description="$1"
    local command="$2"

    total_checks=$((total_checks + 1))
    echo -n "[$total_checks] Checking $description... "

    if eval "$command" >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        passed_checks=$((passed_checks + 1))
        return 0
    else
        echo -e "${RED}✗${NC}"
        failed_checks=$((failed_checks + 1))
        return 1
    fi
}

echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE} PRODUCTION READINESS CHECK${NC}"
echo -e "${BLUE}===========================================${NC}"
echo

# File checks
echo -e "${YELLOW}File Checks:${NC}"
check "docker-compose.prod.yml exists" "test -f docker-compose.prod.yml"
check ".env.prod exists" "test -f .env.prod"
check "nginx/nginx-prod.conf exists" "test -f nginx/nginx-prod.conf"
check ".gitignore exists" "test -f .gitignore"
check ".dockerignore exists" "test -f .dockerignore"
echo

# Service directories
echo -e "${YELLOW}Service Directories:${NC}"
check "platform-bot directory" "test -d platform-bot"
check "factory-service directory" "test -d factory-service"
check "web-api directory" "test -d web-api"
check "web-panel directory" "test -d web-panel"
check "notification-service directory" "test -d notification-service"
check "shared/logging directory" "test -d shared/logging"
echo

# Dockerfiles
echo -e "${YELLOW}Dockerfiles:${NC}"
check "platform-bot Dockerfile" "test -f platform-bot/Dockerfile"
check "factory-service Dockerfile" "test -f factory-service/Dockerfile"
check "web-api Dockerfile" "test -f web-api/Dockerfile"
check "web-panel Dockerfile" "test -f web-panel/Dockerfile"
check "notification-service Dockerfile" "test -f notification-service/Dockerfile"
check "shared/logging Dockerfile" "test -f shared/logging/Dockerfile"
echo

# Scripts
echo -e "${YELLOW}Scripts:${NC}"
check "generate-secrets.sh executable" "test -x scripts/generate-secrets.sh"
check "generate-secrets.py executable" "test -x scripts/generate-secrets.py"
check "deploy-to-vps.sh executable" "test -x scripts/deploy-to-vps.sh"
check "test-prod-locally.sh executable" "test -x scripts/test-prod-locally.sh"
echo

# Environment validation
echo -e "${YELLOW}Environment Variables:${NC}"

if [ -f ".env.prod" ]; then
    source .env.prod 2>/dev/null || true

    check "SERVER_DOMAIN configured" "[ -n '$SERVER_DOMAIN' ] && [ '$SERVER_DOMAIN' != 'yourdomain.com' ]"
    check "WEBHOOK_BASE_URL configured" "[ -n '$WEBHOOK_BASE_URL' ] && [ '$WEBHOOK_BASE_URL' != 'https://yourdomain.com' ]"
    check "POSTGRES_PASSWORD set" "[ -n '$POSTGRES_PASSWORD' ] && [[ '$POSTGRES_PASSWORD' != *'CHANGE_THIS'* ]]"
    check "REDIS_PASSWORD set" "[ -n '$REDIS_PASSWORD' ] && [[ '$REDIS_PASSWORD' != *'CHANGE_THIS'* ]]"
    check "ENCRYPTION_KEY set" "[ -n '$ENCRYPTION_KEY' ] && [[ '$ENCRYPTION_KEY' != *'CHANGE_THIS'* ]]"
    check "JWT_SECRET_KEY set" "[ -n '$JWT_SECRET_KEY' ] && [[ '$JWT_SECRET_KEY' != *'CHANGE_THIS'* ]]"
else
    echo -e "${RED}  ✗ .env.prod not found - cannot check variables${NC}"
    total_checks=$((total_checks + 6))
    failed_checks=$((failed_checks + 6))
fi
echo

# System tools
echo -e "${YELLOW}Local System Tools:${NC}"
check "Docker installed" "command -v docker"
check "Docker Compose installed" "command -v docker-compose"
check "SSH client installed" "command -v ssh"
check "rsync installed" "command -v rsync"
echo

# Docker Compose validation
echo -e "${YELLOW}Docker Compose Configuration:${NC}"
if command -v docker-compose &>/dev/null; then
    check "docker-compose.prod.yml is valid" "docker-compose -f docker-compose.prod.yml config >/dev/null 2>&1"
else
    echo -e "${YELLOW}  ⚠ Docker Compose not installed - skipping validation${NC}"
fi
echo

# Summary
echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE} SUMMARY${NC}"
echo -e "${BLUE}===========================================${NC}"
echo "Total checks: $total_checks"
echo -e "${GREEN}Passed: $passed_checks${NC}"
if [ $failed_checks -gt 0 ]; then
    echo -e "${RED}Failed: $failed_checks${NC}"
    echo
    echo -e "${YELLOW}Please fix the failed checks before deploying to production.${NC}"
    exit 1
else
    echo -e "${GREEN}All checks passed!${NC}"
    echo
    echo -e "${GREEN}Your project is ready for production deployment! 🚀${NC}"
    echo
    echo "Next steps:"
    echo "  1. Generate secrets: ./scripts/generate-secrets.sh"
    echo "  2. Configure .env.prod: nano .env.prod"
    echo "  3. Test locally: ./scripts/test-prod-locally.sh"
    echo "  4. Deploy to VPS: ./scripts/deploy-to-vps.sh"
fi
echo -e "${BLUE}===========================================${NC}"
