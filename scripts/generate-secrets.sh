#!/bin/bash
# ============================================
# Generate secure secrets for production deployment
# Uses only bash - no Python required
# ============================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

generate_password() {
    local length=$1
    LC_ALL=C tr -dc 'A-Za-z0-9!@#$%^&*()_+-=' < /dev/urandom | head -c $length
}

generate_base64_key() {
    local length=$1
    LC_ALL=C tr -dc 'A-Za-z0-9+/=' < /dev/urandom | head -c $length
}

echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE} SECURE SECRETS GENERATOR${NC}"
echo -e "${BLUE}===========================================${NC}"
echo

echo -e "${GREEN}🔐 POSTGRES_PASSWORD:${NC}"
echo -e "   $(generate_password 48)"
echo

echo -e "${GREEN}🔐 REDIS_PASSWORD:${NC}"
echo -e "   $(generate_password 48)"
echo

echo -e "${GREEN}🔐 ENCRYPTION_KEY (Base64):${NC}"
echo -e "   $(generate_base64_key 44)"
echo

echo -e "${GREEN}🔐 JWT_SECRET_KEY:${NC}"
echo -e "   $(generate_base64_key 64)"
echo

echo -e "${GREEN}🔐 PLATFORM_BOT_WEBHOOK_SECRET:${NC}"
echo -e "   $(generate_base64_key 32)"
echo

echo -e "${BLUE}===========================================${NC}"
echo -e "${YELLOW}⚠️  Copy these values to your .env.prod file${NC}"
echo -e "${YELLOW}⚠️  Keep these secrets secure!${NC}"
echo -e "${BLUE}===========================================${NC}"
