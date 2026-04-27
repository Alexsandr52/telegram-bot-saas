#!/bin/bash
# ============================================
# Telegram Bot SaaS - Database Backup Script
# Automated backup with retention policy
# ============================================

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
RETENTION_WEEKS="${BACKUP_RETENTION_WEEKS:-8}"
RETENTION_MONTHS="${BACKUP_RETENTION_MONTHS:-6}"

# Container names
DB_CONTAINER="${DB_CONTAINER:-bot_saas_db_prod}"

# Backup paths
DAILY_DIR="$BACKUP_DIR/daily"
WEEKLY_DIR="$BACKUP_DIR/weekly"
MONTHLY_DIR="$BACKUP_DIR/monthly"

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

# Create backup directories
create_directories() {
    log "Creating backup directories..."
    mkdir -p "$DAILY_DIR" "$WEEKLY_DIR" "$MONTHLY_DIR"
}

# Check if database container is running
check_database() {
    if ! docker ps | grep -q "$DB_CONTAINER"; then
        error "Database container $DB_CONTAINER is not running!"
        exit 1
    fi
}

# Backup database
backup_database() {
    local backup_type=$1
    local backup_dir=$2

    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="backup_${timestamp}.sql.gz"

    log "Creating $backup_type backup: $backup_file"

    # Create backup
    if docker exec "$DB_CONTAINER" pg_dump \
        -U "${POSTGRES_USER:-postgres}" \
        -d "${POSTGRES_DB:-bot_saas}" \
        -x -O 2>/dev/null | gzip > "$backup_dir/$backup_file"; then

        if [ -f "$backup_dir/$backup_file" ]; then
            local size=$(du -h "$backup_dir/$backup_file" | cut -f1)
            log "✅ Backup created successfully ($size)"
            echo "$backup_dir/$backup_file"
            return 0
        else
            error "Backup file was not created!"
            return 1
        fi
    else
        error "Failed to create backup!"
        return 1
    fi
}

# Clean old backups
cleanup_old_backups() {
    log "Cleaning old backups..."

    # Clean daily backups
    if [ "$RETENTION_DAYS" -gt 0 ]; then
        find "$DAILY_DIR" -name "backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
        log "Cleaned daily backups older than $RETENTION_DAYS days"
    fi

    # Clean weekly backups
    if [ "$RETENTION_WEEKS" -gt 0 ]; then
        find "$WEEKLY_DIR" -name "backup_*.sql.gz" -mtime +$((RETENTION_WEEKS * 7)) -delete
        log "Cleaned weekly backups older than $RETENTION_WEEKS weeks"
    fi

    # Clean monthly backups
    if [ "$RETENTION_MONTHS" -gt 0 ]; then
        find "$MONTHLY_DIR" -name "backup_*.sql.gz" -mtime +$((RETENTION_MONTHS * 30)) -delete
        log "Cleaned monthly backups older than $RETENTION_MONTHS months"
    fi
}

# Count backups
count_backups() {
    local daily_count=$(ls -1 "$DAILY_DIR"/*.sql.gz 2>/dev/null | wc -l)
    local weekly_count=$(ls -1 "$WEEKLY_DIR"/*.sql.gz 2>/dev/null | wc -l)
    local monthly_count=$(ls -1 "$MONTHLY_DIR"/*.sql.gz 2>/dev/null | wc -l)

    echo -e "\n${GREEN}=== Backup Summary ===${NC}"
    echo -e "Daily backups:   $daily_count"
    echo -e "Weekly backups:  $weekly_count"
    echo -e "Monthly backups: $monthly_count"
}

# ============================================
# Main
# ============================================

log "=== Starting Database Backup ==="
echo ""

# Check prerequisites
check_database
create_directories

# Determine backup type based on day of week
DAY_OF_WEEK=$(date +%u)  # 1-7 (1=Monday)
DAY_OF_MONTH=$(date +%d)

# Always create daily backup
backup_database "daily" "$DAILY_DIR"

# Weekly backup on Sunday (day 7)
if [ "$DAY_OF_WEEK" -eq 7 ]; then
    backup_database "weekly" "$WEEKLY_DIR"
fi

# Monthly backup on 1st of month
if [ "$DAY_OF_MONTH" -eq 1 ]; then
    backup_database "monthly" "$MONTHLY_DIR"
fi

# Cleanup old backups
cleanup_old_backups

# Show summary
count_backups

log "=== Backup Completed ==="
