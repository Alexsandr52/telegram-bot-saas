#!/bin/bash
# ============================================
# Telegram Bot SaaS - Database Restore Script
# Restore database from backup
# ============================================

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================
# Configuration
# ============================================

# Load environment variables
if [ -f "../.env" ]; then
    export $(cat ../.env | grep -v '^#' | grep -v '^$' | xargs)
elif [ -f "../.env.prod" ]; then
    export $(cat ../.env.prod | grep -v '^#' | grep -v '^$' | xargs)
else
    echo -e "${RED}ERROR: .env or .env.prod file not found!${NC}"
    exit 1
fi

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups/postgres}"
DB_CONTAINER="${DB_CONTAINER:-bot_saas_db_prod}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-bot_saas}"

# ============================================
# Functions
# ============================================

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# List available backups
list_backups() {
    echo -e "${BLUE}=== Available Backups ===${NC}"
    echo ""

    # Daily backups
    if [ -d "$BACKUP_DIR/daily" ]; then
        echo -e "${YELLOW}Daily backups:${NC}"
        ls -lh "$BACKUP_DIR/daily"/*.sql.gz 2>/dev/null | tail -10 || echo "  No daily backups found"
        echo ""
    fi

    # Weekly backups
    if [ -d "$BACKUP_DIR/weekly" ]; then
        echo -e "${YELLOW}Weekly backups:${NC}"
        ls -lh "$BACKUP_DIR/weekly"/*.sql.gz 2>/dev/null || echo "  No weekly backups found"
        echo ""
    fi

    # Monthly backups
    if [ -d "$BACKUP_DIR/monthly" ]; then
        echo -e "${YELLOW}Monthly backups:${NC}"
        ls -lh "$BACKUP_DIR/monthly"/*.sql.gz 2>/dev/null || echo "  No monthly backups found"
        echo ""
    fi
}

# Check database container
check_database() {
    if ! docker ps | grep -q "$DB_CONTAINER"; then
        error "Database container $DB_CONTAINER is not running!"
        exit 1
    fi

    log "Database container is running"
}

# Stop all services except database
stop_services() {
    log "Stopping application services..."
    docker compose -f ../docker-compose.prod.yml stop platform-bot factory-service web-api web-panel notification-service 2>/dev/null || true
    sleep 2
}

# Start services
start_services() {
    log "Starting application services..."
    docker compose -f ../docker-compose.prod.yml up -d
}

# Restore from backup file
restore_backup() {
    local backup_file=$1

    if [ ! -f "$backup_file" ]; then
        error "Backup file not found: $backup_file"
        exit 1
    fi

    log "Restoring from: $backup_file"
    info "Backup size: $(du -h $backup_file | cut -f1)"

    # Get backup info
    if command -v gunzip &> /dev/null; then
        local db_name=$(gunzip -c "$backup_file" | head -1 | sed -n 's/.*-- Name: \(.*\)/\1/p')
        info "Database name: ${db_name:-Unknown}"
    fi

    # Stop services
    stop_services

    # Drop existing database
    log "Dropping existing database..."
    docker exec "$DB_CONTAINER" dropdb \
        -U "$POSTGRES_USER" \
        --if-exists \
        "$POSTGRES_DB"

    # Create new database
    log "Creating new database..."
    docker exec "$DB_CONTAINER" createdb \
        -U "$POSTGRES_USER" \
        "$POSTGRES_DB"

    # Restore backup
    log "Restoring database..."
    if gunzip -c "$backup_file" | docker exec -i "$DB_CONTAINER" psql \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB"; then

        log "✅ Database restored successfully!"
    else
        error "Failed to restore database!"
        start_services
        exit 1
    fi

    # Start services
    start_services

    # Verify restore
    log "Verifying database..."
    sleep 5

    local tables_count=$(docker exec "$DB_CONTAINER" psql \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'" 2>/dev/null || echo "0")

    info "Tables in database: $tables_count"

    if [ "$tables_count" -gt 0 ]; then
        log "✅ Restore verified successfully!"
    else
        warning "Database appears to be empty. Please check the backup file."
    fi
}

# Restore latest backup of type
restore_latest() {
    local backup_type=$1
    local backup_dir="$BACKUP_DIR/$backup_type"

    if [ ! -d "$backup_dir" ]; then
        error "Backup directory not found: $backup_dir"
        exit 1
    fi

    # Find latest backup
    local latest_backup=$(ls -t "$backup_dir"/*.sql.gz 2>/dev/null | head -1)

    if [ -z "$latest_backup" ]; then
        error "No backups found in $backup_dir"
        exit 1
    fi

    info "Latest $backup_type backup: $(basename $latest_backup)"

    # Confirm restore
    echo -e "${YELLOW}⚠️  WARNING: This will REPLACE the current database!${NC}"
    read -p "Are you sure you want to restore? (yes/no): " confirm
    echo

    if [[ $confirm =~ ^[Yy][Ee][Ss]$ ]]; then
        restore_backup "$latest_backup"
    else
        info "Restore cancelled"
    fi
}

# ============================================
# Main
# ============================================

# Parse arguments
case "$1" in
    --list|-l)
        list_backups
        exit 0
        ;;

    --latest-daily)
        check_database
        restore_latest "daily"
        exit 0
        ;;

    --latest-weekly)
        check_database
        restore_latest "weekly"
        exit 0
        ;;

    --latest-monthly)
        check_database
        restore_latest "monthly"
        exit 0
        ;;

    --help|-h)
        echo "Usage: $0 [options] [backup_file]"
        echo ""
        echo "Options:"
        echo "  --list, -l              List all available backups"
        echo "  --latest-daily           Restore latest daily backup"
        echo "  --latest-weekly          Restore latest weekly backup"
        echo "  --latest-monthly         Restore latest monthly backup"
        echo "  --help, -h              Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 --list"
        echo "  $0 --latest-daily"
        echo "  $0 /path/to/backup.sql.gz"
        exit 0
        ;;

    "")
        echo "No arguments provided. Use --help for usage."
        list_backups
        exit 1
        ;;

    *)
        # Check if it's a valid backup file
        if [[ $1 == *.sql.gz ]]; then
            check_database
            restore_backup "$1"
        else
            error "Invalid backup file: $1"
            echo "Use --help for usage"
            exit 1
        fi
        ;;
esac

log "=== Restore Completed ==="
