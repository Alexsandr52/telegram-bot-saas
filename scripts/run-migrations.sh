#!/bin/bash
# ============================================
# Telegram Bot SaaS - Database Migration Runner
# Applies database migrations in order
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
DB_CONTAINER="${DB_CONTAINER:-bot_saas_db_prod}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-bot_saas}"
MIGRATIONS_DIR="../database/migrations"
SCHEMA_FILE="../database/schema.sql"

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

# Check if database is running
check_database() {
    if ! docker ps | grep -q "$DB_CONTAINER"; then
        error "Database container $DB_CONTAINER is not running!"
        error "Please start the database first"
        exit 1
    fi

    log "Database container is running"
}

# Get applied migrations
get_applied_migrations() {
    # Check if migrations table exists
    if docker exec "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'schema_migrations')" 2>/dev/null; then

        # Get applied migrations
        docker exec "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
            "SELECT version FROM schema_migrations ORDER BY applied_at ASC" 2>/dev/null || echo ""
    else
        echo ""
    fi
}

# Apply initial schema
apply_schema() {
    log "Applying initial schema..."

    if docker exec -i "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$SCHEMA_FILE"; then
        log "✅ Schema applied successfully"

        # Create migrations tracking table
        create_migrations_table

        # Mark schema as applied
        docker exec "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
            "INSERT INTO schema_migrations (version, description) VALUES ('000_schema', 'Initial database schema');" 2>/dev/null || true

        return 0
    else
        error "Failed to apply schema!"
        return 1
    fi
}

# Create migrations tracking table
create_migrations_table() {
    docker exec "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id SERIAL PRIMARY KEY,
            version VARCHAR(50) UNIQUE NOT NULL,
            description TEXT,
            applied_at TIMESTAMPTZ DEFAULT NOW()
        );
    " 2>/dev/null || true
}

# Apply a single migration
apply_migration() {
    local migration_file=$1
    local migration_version=$(basename "$migration_file" | cut -d'_' -f1)

    log "Applying migration: $migration_version"

    # Check if already applied
    local is_applied=$(docker exec "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
        "SELECT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '$migration_version');" 2>/dev/null)

    if [ "$is_applied" = "t" ]; then
        info "Migration $migration_version already applied, skipping"
        return 0
    fi

    # Apply migration
    if docker exec -i "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$migration_file"; then
        log "✅ Migration $migration_version applied successfully"

        # Record migration
        docker exec "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
            "INSERT INTO schema_migrations (version, description) VALUES ('$migration_version', 'Migration from $(basename $migration_file)');" 2>/dev/null || true

        return 0
    else
        error "Failed to apply migration $migration_version!"
        return 1
    fi
}

# List available migrations
list_migrations() {
    echo -e "${BLUE}=== Available Migrations ===${NC}"
    echo ""

    # Applied migrations
    echo -e "${YELLOW}Applied migrations:${NC}"
    local applied=$(get_applied_migrations)
    if [ -n "$applied" ]; then
        echo "$applied"
    else
        echo "  None"
    fi
    echo ""

    # Available migration files
    echo -e "${YELLOW}Pending migrations:${NC}"
    if [ -d "$MIGRATIONS_DIR" ]; then
        for file in $MIGRATIONS_DIR/*.sql; do
            if [ -f "$file" ]; then
                local version=$(basename "$file" | cut -d'_' -f1)
                local is_pending=$(echo "$applied" | grep -c "$version" || echo "1")
                if [ "$is_pending" -eq 0 ]; then
                    echo "  - $(basename $file)"
                fi
            fi
        done
    else
        echo "  No migration files found"
    fi
}

# ============================================
# Main
# ============================================

case "$1" in
    --list|-l)
        check_database
        list_migrations
        exit 0
        ;;

    --force|-f)
        check_database
        warning "Force mode: applying all migrations including already applied ones!"
        echo -e "${RED}⚠️  This may cause errors if migrations are not idempotent!${NC}"
        read -p "Continue? (yes/no): " confirm
        echo

        if [[ $confirm =~ ^[Yy][Ee][Ss]$ ]]; then
            # Apply migrations in order
            for file in $MIGRATIONS_DIR/*.sql; do
                if [ -f "$file" ]; then
                    apply_migration "$file" || exit 1
                fi
            done
            log "All migrations applied"
        else
            info "Cancelled"
        fi
        exit 0
        ;;

    --init|-i)
        check_database
        log "Initializing database with schema..."
        apply_schema || exit 1
        log "Database initialized successfully"
        exit 0
        ;;

    --help|-h)
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --list, -l              List applied and pending migrations"
        echo "  --init, -i             Apply initial schema (first time setup)"
        echo "  --force, -f             Apply all migrations (including already applied)"
        echo "  --help, -h              Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 --list"
        echo "  $0 --init"
        echo "  $0"
        exit 0
        ;;

    "")
        # Default: apply pending migrations
        check_database

        # Check if schema exists
        local schema_exists=$(docker exec "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'masters');" 2>/dev/null)

        if [ "$schema_exists" != "t" ]; then
            warning "Database schema not found. Run --init first."
            exit 1
        fi

        # Apply pending migrations
        log "Applying pending migrations..."
        local applied_count=0

        for file in $MIGRATIONS_DIR/*.sql; do
            if [ -f "$file" ]; then
                apply_migration "$file" && ((applied_count++)) || exit 1
            fi
        done

        if [ $applied_count -eq 0 ]; then
            info "No pending migrations to apply"
        else
            log "Applied $applied_count migration(s)"
        fi

        list_migrations
        log "Migration completed"
        exit 0
        ;;

    *)
        error "Unknown option: $1"
        echo "Use --help for usage"
        exit 1
        ;;
esac
