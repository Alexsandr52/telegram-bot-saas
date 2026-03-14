#!/bin/bash

# ============================================
# Ngrok Setup Script for Local Development
# ============================================
# This script sets up ngrok tunnel for local webhook testing

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
NGROK_CONFIG_DIR="$HOME/.ngrok2"
NGROK_CONFIG_FILE="$NGROK_CONFIG_DIR/ngrok.yml"
WEBHOOK_DOMAIN="${NGROK_DOMAIN:-}"
SERVER_PORT="${SERVER_PORT:-80}"

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  Ngrok Setup for Webhooks${NC}"
echo -e "${GREEN}======================================${NC}"

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo -e "${YELLOW}Ngrok not found. Installing...${NC}"
    echo ""

    # Detect OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if [[ "$(uname -m)" == "arm64" ]]; then
            NGROK_URL="https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-darwin-arm64.zip"
        else
            NGROK_URL="https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-darwin-amd64.zip"
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if [[ "$(uname -m)" == "aarch64" ]]; then
            NGROK_URL="https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-arm64.zip"
        else
            NGROK_URL="https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-amd64.zip"
        fi
    else
        echo -e "${RED}Unsupported OS: $OSTYPE${NC}"
        exit 1
    fi

    # Download and install
    echo "Downloading ngrok from: $NGROK_URL"
    curl -sL "$NGROK_URL" -o /tmp/ngrok.zip
    unzip -o /tmp/ngrok.zip -d /tmp/
    sudo mv /tmp/ngrok /usr/local/bin/
    rm /tmp/ngrok.zip

    echo -e "${GREEN}Ngrok installed successfully!${NC}"
else
    echo -e "${GREEN}Ngrok is already installed${NC}"
fi

echo ""
echo -e "${YELLOW}Checking ngrok configuration...${NC}"

# Create config directory if not exists
mkdir -p "$NGROK_CONFIG_DIR"

# Check if ngrok is authenticated
if ngrok diagnose | grep -q "authtoken"; then
    echo -e "${YELLOW}Ngrok is not authenticated.${NC}"
    echo ""
    echo "Please sign up at https://dashboard.ngrok.com/signup"
    echo "Then run: ngrok config add-authtoken YOUR_AUTH_TOKEN"
    echo ""
    read -p "Do you want to set authtoken now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter your ngrok authtoken: " NGROK_TOKEN
        ngrok config add-authtoken "$NGROK_TOKEN"
        echo -e "${GREEN}Authtoken set successfully!${NC}"
    else
        echo -e "${YELLOW}Skipping authtoken setup${NC}"
    fi
fi

echo ""
echo -e "${YELLOW}Starting ngrok tunnel...${NC}"

# Create ngrok config file
cat > "$NGROK_CONFIG_FILE" <<EOF
version: "2"
authtoken: $(grep -o 'authtoken: [^ ]*' "$NGROK_CONFIG_FILE" 2>/dev/null | cut -d' ' -f2 || echo '')

tunnels:
  bot-webhook:
    proto: http
    addr: $SERVER_PORT
    bind_tls: true
    inspect: false
    web_addr: localhost:4040

  # For production domain (if using custom domain)
  custom-domain:
    proto: http
    addr: $SERVER_PORT
    hostname: $WEBHOOK_DOMAIN
    bind_tls: true
EOF

# Check if using custom domain
if [ -n "$WEBHOOK_DOMAIN" ]; then
    echo -e "${GREEN}Using custom domain: $WEBHOOK_DOMAIN${NC}"
    ngrok start custom-domain --log=stdout > /tmp/ngrok.log 2>&1 &
else
    echo -e "${YELLOW}Starting ngrok with random domain...${NC}"
    ngrok start bot-webhook --log=stdout > /tmp/ngrok.log 2>&1 &
fi

NGROK_PID=$!

# Wait for ngrok to start
echo "Waiting for ngrok to start..."
sleep 3

# Extract the public URL
if [ -n "$WEBHOOK_DOMAIN" ]; then
    WEBHOOK_URL="https://$WEBHOOK_DOMAIN"
else
    WEBHOOK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"[^"]*' | cut -d'"' -f4)
fi

if [ -z "$WEBHOOK_URL" ]; then
    echo -e "${RED}Failed to get webhook URL from ngrok${NC}"
    cat /tmp/ngrok.log
    exit 1
fi

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  Ngrok is running!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "${YELLOW}Webhook URL: ${GREEN}$WEBHOOK_URL${NC}"
echo -e "${YELLOW}Webhook endpoint: ${GREEN}${WEBHOOK_URL}/webhook/{bot_id}${NC}"
echo ""
echo -e "${YELLOW}Ngrok Dashboard: ${GREEN}http://localhost:4040${NC}"
echo ""
echo -e "${YELLOW}Use this URL for:${NC}"
echo "  1. Setting webhooks in Telegram (@BotFather)"
echo "  2. Testing bot webhooks locally"
echo ""
echo -e "${YELLOW}To stop ngrok:${NC}"
echo "  kill $NGROK_PID"
echo "  or press Ctrl+C"

# Export webhook URL for use by other scripts
export WEBHOOK_URL="$WEBHOOK_URL"

# Keep script running
wait $NGROK_PID
