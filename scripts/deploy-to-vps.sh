#!/bin/bash
# ============================================
# Deploy Telegram Bot SaaS to VPS
# ============================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VPS_HOST=""
VPS_USER="root"
PROJECT_DIR="/opt/telegram-bot-saas"
DOMAIN=""

# Print functions
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required commands exist
check_requirements() {
    print_info "Checking local requirements..."

    if ! command -v ssh &> /dev/null; then
        print_error "ssh is not installed"
        exit 1
    fi

    if ! command -v rsync &> /dev/null; then
        print_error "rsync is not installed"
        exit 1
    fi

    print_success "All requirements met"
}

# Get user input
get_input() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}  TELEGRAM BOT SAAS - VPS DEPLOYMENT${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo

    read -p "Enter VPS IP address or hostname: " VPS_HOST
    read -p "Enter SSH username (default: root): " VPS_USER_INPUT
    VPS_USER=${VPS_USER_INPUT:-root}
    read -p "Enter your domain name (e.g., bot.yourdomain.com): " DOMAIN
    read -p "Enter path to .env.prod file (default: .env.prod): " ENV_FILE
    ENV_FILE=${ENV_FILE:-.env.prod}

    echo
    print_warning "Please verify your settings:"
    echo "   VPS Host: $VPS_HOST"
    echo "   SSH User: $VPS_USER"
    echo "   Domain: $DOMAIN"
    echo "   Env File: $ENV_FILE"
    echo
    read -p "Continue? (y/n): " CONFIRM

    if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
        print_error "Deployment cancelled"
        exit 1
    fi
}

# Prepare .env file
prepare_env() {
    print_info "Preparing .env.prod file..."

    if [ ! -f "$ENV_FILE" ]; then
        print_error ".env.prod file not found at $ENV_FILE"
        print_info "Please copy .env.prod.example to .env.prod and fill in your values"
        exit 1
    fi

    # Update domain in env file
    sed -i.bak "s/^SERVER_DOMAIN=.*/SERVER_DOMAIN=$DOMAIN/" "$ENV_FILE"
    sed -i.bak "s/^WEBHOOK_BASE_URL=.*/WEBHOOK_BASE_URL=https:\/\/$DOMAIN/" "$ENV_FILE"
    sed -i.bak "s/^WEB_PANEL_URL=.*/WEB_PANEL_URL=https:\/\/$DOMAIN/" "$ENV_FILE"
    sed -i.bak "s/^CORS_ORIGINS=.*/CORS_ORIGINS=https:\/\/$DOMAIN/" "$ENV_FILE"

    rm -f "${ENV_FILE}.bak"

    print_success "Environment file prepared"
}

# Prepare files for deployment
prepare_files() {
    print_info "Preparing files for deployment..."

    # Create temporary deployment directory
    DEPLOY_DIR=$(mktemp -d)
    trap "rm -rf $DEPLOY_DIR" EXIT

    # Copy necessary files
    mkdir -p "$DEPLOY_DIR"
    cp -r \
        platform-bot \
        factory-service \
        web-api \
        web-panel \
        notification-service \
        billing-service \
        bot-template \
        database \
        nginx \
        shared \
        scripts \
        "$DEPLOY_DIR/"

    cp docker-compose.prod.yml "$DEPLOY_DIR/docker-compose.yml"
    cp "$ENV_FILE" "$DEPLOY_DIR/.env"
    cp .gitignore "$DEPLOY_DIR/"

    # Create necessary directories
    mkdir -p "$DEPLOY_DIR/certbot/conf"
    mkdir -p "$DEPLOY_DIR/certbot/www"
    mkdir -p "$DEPLOY_DIR/backups/postgres"
    mkdir -p "$DEPLOY_DIR/bot-templates"
    mkdir -p "$DEPLOY_DIR/logs/api"
    mkdir -p "$DEPLOY_DIR/logs/factory"
    mkdir -p "$DEPLOY_DIR/logs/notifications"
    mkdir -p "$DEPLOY_DIR/logs/central"

    # Create dockerignore
    cat > "$DEPLOY_DIR/.dockerignore" << 'EOF'
.git
.gitignore
.env
.env.local
.env.*
*.md
scripts
README.md
__pycache__
*.pyc
.DS_Store
EOF

    echo "$DEPLOY_DIR"
}

# Deploy to VPS
deploy_to_vps() {
    local DEPLOY_DIR=$1

    print_info "Connecting to VPS..."

    # Check if SSH connection works
    if ! ssh -o ConnectTimeout=10 "$VPS_USER@$VPS_HOST" "echo 'Connection successful'" 2>/dev/null; then
        print_error "Cannot connect to VPS. Please check your SSH credentials."
        exit 1
    fi

    print_success "Connected to VPS"

    # Install Docker on VPS if not present
    print_info "Checking Docker installation on VPS..."
    ssh "$VPS_USER@$VPS_HOST" bash << 'ENDSSH'
        if ! command -v docker &> /dev/null; then
            echo "Installing Docker..."
            curl -fsSL https://get.docker.com -o get-docker.sh
            sh get-docker.sh
            usermod -aG docker $USER
            rm -f get-docker.sh
            echo "Docker installed successfully"
        else
            echo "Docker is already installed"
        fi

        if ! command -v docker-compose &> /dev/null; then
            echo "Installing Docker Compose..."
            curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
            chmod +x /usr/local/bin/docker-compose
            echo "Docker Compose installed successfully"
        else
            echo "Docker Compose is already installed"
        fi
ENDSSH

    # Sync files to VPS
    print_info "Syncing files to VPS (this may take a while)..."

    ssh "$VPS_USER@$VPS_HOST" "mkdir -p $PROJECT_DIR"

    rsync -avz --delete \
        --exclude 'node_modules' \
        --exclude '__pycache__' \
        --exclude '*.pyc' \
        --exclude '.git' \
        --exclude '.env.local' \
        "$DEPLOY_DIR/" \
        "$VPS_USER@$VPS_HOST:$PROJECT_DIR/"

    print_success "Files synced successfully"
}

# Setup SSL certificates
setup_ssl() {
    print_info "Setting up SSL certificates..."

    ssh "$VPS_USER@$VPS_HOST" bash << ENDSSH
        cd $PROJECT_DIR

        # Stop nginx temporarily to get certificates
        docker-compose stop nginx

        # Get initial certificates
        docker run --rm \
            -v ./certbot/conf:/etc/letsencrypt \
            -v ./certbot/www:/var/www/certbot \
            certbot/certbot:latest \
            certonly --webroot -w /var/www/certbot \
            --email admin@$DOMAIN \
            --agree-tos \
            --no-eff-email \
            -d $DOMAIN

        # Start nginx
        docker-compose up -d nginx

        echo "SSL certificates installed successfully"
ENDSSH

    print_success "SSL certificates configured"
}

# Start services
start_services() {
    print_info "Starting Docker services..."

    ssh "$VPS_USER@$VPS_HOST" bash << ENDSSH
        cd $PROJECT_DIR

        # Build images
        echo "Building Docker images..."
        docker-compose build

        # Start services
        echo "Starting services..."
        docker-compose up -d

        # Wait for services to be ready
        echo "Waiting for services to start..."
        sleep 30

        # Check service status
        echo ""
        echo "Service Status:"
        docker-compose ps
ENDSSH

    print_success "Services started"
}

# Print deployment summary
print_summary() {
    echo
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}  DEPLOYMENT COMPLETED SUCCESSFULLY${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo
    echo "🎉 Your Telegram Bot SaaS is now deployed!"
    echo
    echo "📋 Next Steps:"
    echo "   1. Visit https://$DOMAIN to access the web panel"
    echo "   2. Set up your platform bot token in .env"
    echo "   3. Configure webhook URL: https://$DOMAIN/webhook/platform"
    echo "   4. Start creating bots!"
    echo
    echo "🔧 Useful Commands:"
    echo "   View logs: ssh $VPS_USER@$VPS_HOST 'cd $PROJECT_DIR && docker-compose logs -f'"
    echo "   Restart: ssh $VPS_USER@$VPS_HOST 'cd $PROJECT_DIR && docker-compose restart'"
    echo "   Stop: ssh $VPS_USER@$VPS_HOST 'cd $PROJECT_DIR && docker-compose stop'"
    echo "   Update: ssh $VPS_USER@$VPS_HOST 'cd $PROJECT_DIR && docker-compose pull && docker-compose up -d'"
    echo
    echo -e "${YELLOW}⚠️  Remember to:"NC"
    echo "   - Backup your .env file"
    echo "   - Monitor your VPS resources"
    echo "   - Keep your system updated"
    echo "   - Set up automated backups"
    echo
}

# Main execution
main() {
    check_requirements
    get_input
    prepare_env

    DEPLOY_DIR=$(prepare_files)
    deploy_to_vps "$DEPLOY_DIR"
    setup_ssl
    start_services
    print_summary
}

# Run main function
main
