#!/bin/bash
# ============================================
# Telegram Bot SaaS - Webhook Setup Script
# ============================================

set -e

# ============================================
# Configuration
# ============================================

# Load environment variables
if [ -f "../.env" ]; then
    export $(cat ../.env | grep -v '^#' | xargs)
elif [ -f "../.env.prod" ]; then
    export $(cat ../.env.prod | grep -v '^#' | xargs)
else
    echo "ERROR: .env file not found!"
    exit 1
fi

WEBHOOK_BASE_URL="${WEBHOOK_BASE_URL}"
WEBHOOK_SECRET="${PLATFORM_BOT_WEBHOOK_SECRET}"
PLATFORM_BOT_TOKEN="${PLATFORM_BOT_TOKEN}"

if [ -z "$WEBHOOK_BASE_URL" ]; then
    echo "ERROR: WEBHOOK_BASE_URL not set in .env file"
    exit 1
fi

if [ -z "$WEBHOOK_SECRET" ]; then
    echo "ERROR: PLATFORM_BOT_WEBHOOK_SECRET not set in .env file"
    exit 1
fi

if [ -z "$PLATFORM_BOT_TOKEN" ]; then
    echo "ERROR: PLATFORM_BOT_TOKEN not set in .env file"
    exit 1
fi

# ============================================
# Functions
# ============================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

check_ssl() {
    local domain=$(echo "$WEBHOOK_BASE_URL" | sed -e 's|https://||' -e 's|/.*||')
    local port=$(echo "$WEBHOOK_BASE_URL" | sed -e 's|.*:||' | sed -e 's|/.*||')

    log "Checking SSL certificate for $domain..."

    if command -v openssl &> /dev/null; then
        echo | openssl s_client -servername "$domain" -connect "$domain:443" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || {
            log "⚠️  SSL certificate check failed"
            return 1
        }

        log "✓ SSL certificate is valid"
        return 0
    else
        log "⚠️  openssl not found, skipping SSL check"
        return 0
    fi
}

check_webhook_reachability() {
    local webhook_url="$WEBHOOK_BASE_URL/webhook/platform"
    log "Testing webhook URL reachability: $webhook_url"

    if command -v curl &> /dev/null; then
        http_code=$(curl -s -o /dev/null -w "%{http_code}" "$webhook_url" || echo "000")

        if [ "$http_code" = "404" ] || [ "$http_code" = "405" ]; then
            log "✓ Webhook URL is reachable (HTTP $http_code - expected for webhook)"
            return 0
        elif [ "$http_code" = "200" ] || [ "$http_code" = "401" ]; then
            log "✓ Webhook URL is reachable (HTTP $http_code)"
            return 0
        elif [ "$http_code" = "000" ]; then
            log "✗ Cannot connect to webhook URL"
            return 1
        else
            log "⚠️  Unexpected HTTP code: $http_code"
            return 1
        fi
    else
        log "⚠️  curl not found, skipping reachability check"
        return 0
    fi
}

set_webhook() {
    local bot_token=$1
    local webhook_path=$2
    local webhook_url="${WEBHOOK_BASE_URL}${webhook_path}"

    log "Setting webhook for bot..."
    log "URL: $webhook_url"
    log "Path: $webhook_path"

    local response=$(curl -s -X POST "https://api.telegram.org/bot${bot_token}/setWebhook" \
        -H "Content-Type: application/json" \
        -d "{
            \"url\": \"${webhook_url}\",
            \"secret_token\": \"${WEBHOOK_SECRET}\",
            \"drop_pending_updates\": true
        }")

    local result=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('result', 'FAILED'))")

    if [ "$result" = "True" ] || [ "$result" = "true" ]; then
        log "✓ Webhook set successfully"
        return 0
    else
        local error_msg=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('description', 'Unknown error'))")
        log "✗ Failed to set webhook: $error_msg"
        return 1
    fi
}

get_webhook_info() {
    local bot_token=$1

    log "Getting webhook info..."

    local response=$(curl -s "https://api.telegram.org/bot${bot_token}/getWebhookInfo")

    local result=$(echo "$response" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin).get('result', {}), indent=2))")

    echo "$result"
}

delete_webhook() {
    local bot_token=$1

    log "Deleting webhook..."

    local response=$(curl -s -X POST "https://api.telegram.org/bot${bot_token}/deleteWebhook")

    local result=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('result', 'FAILED'))")

    if [ "$result" = "True" ] || [ "$result" = "true" ]; then
        log "✓ Webhook deleted successfully"
        return 0
    else
        log "✗ Failed to delete webhook"
        return 1
    fi
}

# ============================================
# Main
# ============================================

log "=== Telegram Webhook Setup ==="

# Check SSL certificate
check_ssl

# Check webhook reachability
check_webhook_reachability

# Get current webhook info
log ""
log "Current webhook info:"
get_webhook_info "$PLATFORM_BOT_TOKEN"

log ""

# Ask user if they want to set the webhook
read -p "Do you want to set the webhook now? (yes/no): " -r
echo

if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    # Set webhook
    set_webhook "$PLATFORM_BOT_TOKEN" "/webhook/platform"

    log ""
    log "Verifying webhook..."

    # Get webhook info again
    get_webhook_info "$PLATFORM_BOT_TOKEN"

    log ""
    log "=== Webhook setup completed ==="
else
    log "Webhook setup skipped"
fi

exit 0
