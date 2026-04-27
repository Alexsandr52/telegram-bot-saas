# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Telegram Bot SaaS** is a microservices platform that allows service providers (hairdressers, nail technicians, brow artists, etc.) to automatically create personal Telegram bots for client bookings.

**Core Concept:** One master's bot = One isolated Docker container

All bot instances are managed automatically through a single platform bot, eliminating the need for programming knowledge.

## Development Commands

### Environment Setup

```bash
# Create .env file from example
make env-setup

# Start all services
docker-compose up -d

# Check service health
make health
```

### Building & Running

```bash
# Build all Docker images
make build

# Start all services
make up

# Restart services
make restart

# Stop all services
make down

# Show logs
make logs
```

### Database Operations

```bash
# Open PostgreSQL shell
make db-shell

# Backup database
make db-backup

# Restore database (specify file)
make db-restore FILE=backups/backup_20250115.sql.gz

# Reset database (WARNING: deletes all data)
make db-reset
```

### Testing & Linting

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests only
make test-integration

# Lint code
make lint

# Format code
make format
```

### Production

```bash
# Start production services
make prod-up

# View production logs
make prod-logs

# Stop production services
make prod-down
```

### Utility Scripts

```bash
# Set webhook for a bot
python3 scripts/set-bot-webhook.py {BOT_TOKEN} set {WEBHOOK_URL}

# Check webhook status
python3 scripts/set-bot-webhook.py {BOT_TOKEN} get

# Remove webhook
python3 scripts/set-bot-webhook.py {BOT_TOKEN} delete

# Update webhooks for all bots
python3 scripts/update-all-webhooks.py

# Setup ngrok for local development
./scripts/setup-ngrok.sh

# Run database migrations
./scripts/run-migrations.sh
```

## Architecture

### Microservices Architecture

The platform consists of several independent microservices, each responsible for a specific domain:

1. **Platform Bot** (port 8001) - Main bot for masters to manage their booking bots
2. **Factory Service** (port 8002) - Docker container management for bot instances
3. **Web API** (port 8000) - REST API for web panel
4. **Web Panel** (port 3000) - Web interface for masters
5. **Notification Service** - System for reminders and alerts
6. **Bot Template** - Template used to create individual bot containers

### Service Communication Flow

```
Telegram API → Platform Bot / Bot Instances
                    ↓
              Nginx Gateway
                    ↓
       ┌────────────┼────────────┐
       ↓            ↓            ↓
  Factory Svc  Web API     Notification Svc
       └────────────┴────────────┘
                    ↓
         PostgreSQL + Redis
```

### Key Architectural Patterns

#### Repository Pattern
Each service uses repository classes for database access (see `platform-bot/src/utils/repositories.py` and `platform-bot/src/utils/db.py`). Repositories are singletons accessed through getter functions like `get_bot_repo()`, `get_master_repo()`, etc.

#### Docker Container Management
Factory Service uses Docker CLI via subprocess to manage bot containers (see `factory-service/src/docker/manager.py`). Each bot container is labeled with `bot_id` for tracking. Container names follow pattern: `bot_{bot_id[:8]}`.

#### Configuration Management
Settings are managed using Pydantic Settings with environment variables (see `platform-bot/src/utils/config.py`). Settings use singleton pattern with `get_settings()` function. Critical settings include:

- `BOT_TOKEN` - Platform bot token from BotFather
- `DATABASE_URL` - PostgreSQL connection URL (must use `postgresql+asyncpg://` for async operations)
- `REDIS_URL` - Redis connection URL
- `TELEGRAM_PROXY` - SOCKS5 proxy for Telegram API (required in Russia)
- `ENCRYPTION_KEY` - Fernet key for token encryption
- `JWT_SECRET_KEY` - JWT secret for web panel authentication

#### Error Logging
All services use centralized error logging system (`shared/error_logging.py`). Errors are logged to `error_logs` database table with categorization and severity levels. Error categories include: `DATABASE`, `NETWORK`, `TELEGRAM_API`, `WEBHOOK`, `AUTHENTICATION`, `BUSINESS_LOGIC`, `SYSTEM`, `EXTERNAL_API`.

### Database Schema

The schema is defined in `database/schema.sql`. Key tables:

- `masters` - Master accounts with Telegram ID
- `bots` - Bot instances with encrypted tokens and container status
- `services` - Services offered by masters
- `schedules` - Working hours configuration
- `appointments` - Client bookings
- `clients` - Client information
- `subscriptions` - Master subscription plans (free, pro, business)
- `notifications_queue` - Queued notifications
- `analytics_events` - Partitioned by month for performance
- `system_logs` - Application logs

Important indexes:
- `idx_appointments_bot_time` - Critical for calendar availability checks
- `idx_appointments_availability` - Composite index for slot availability
- `idx_notifications_send_at` - For notification queue processing

#### PostgreSQL Functions
- `check_slot_availability(bot_id, start_time, end_time)` - Check if time slot is free
- `get_available_slots(bot_id, date, service_id)` - Generate available time slots
- `update_client_stats(client_id)` - Update client visit/spending statistics

### Telegram Bot Implementation

Both Platform Bot and Bot Template use aiogram 3.x framework. Key implementation details:

#### Proxy Support
Critical for Telegram API access in Russia. Configure via `TELEGRAM_PROXY` environment variable (SOCKS5 or HTTP format). Proxy is passed to Bot initialization.

#### Webhook vs Polling
Services can operate in webhook or polling mode based on `BOT_WEBHOOK_MODE` setting. Webhook is preferred for production.

#### Error Handling
All bots use global error handlers (`@dp.errors()`) that:
1. Log errors to database via error_logging system
2. Log to analytics for tracking
3. Send user-friendly error messages

### Container Lifecycle

1. **Creation:** Platform bot requests container creation from Factory Service via REST API
2. **Deployment:** Factory Service creates container from `bot-template` image with bot-specific environment variables
3. **Configuration:** Container loads config from database using `ConfigManager`
4. **Runtime:** Bot runs in container, processes client messages
5. **Management:** Factory Service can start/stop/restart/delete containers
6. **Cleanup:** Containers are removed when bot is deleted

### Security Considerations

- Bot tokens are encrypted in database using Fernet symmetric encryption
- Webhooks are protected with secret tokens
- All bot containers run in isolated Docker network (`bot_saas_network`)
- PostgreSQL uses parameterized queries to prevent SQL injection
- Rate limiting is implemented in nginx

### Development Environment

#### Required Ports
- PostgreSQL: 5432
- Redis: 6379
- pgAdmin: 5050
- Redis Commander: 8082
- Web API: 8000
- Platform Bot: 8001
- Factory Service: 8002
- Web Panel: 3000
- Nginx: 80, 443

#### Database Access
```bash
# Connect to PostgreSQL
docker-compose exec database psql -U postgres -d bot_saas

# Connect to Redis
docker-compose exec redis redis-cli -a redis123
```

#### Log Viewing
```bash
# View all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f platform-bot
docker-compose logs -f factory-service

# View individual bot container logs
docker logs {container_id} -f
```

## Important Notes

### Telegram API in Russia
Telegram API is blocked in Russia. You MUST configure a SOCKS5 or HTTP proxy in `TELEGRAM_PROXY` environment variable for services to work.

### Token Encryption
Never store bot tokens in plaintext. Use the encryption utilities in `platform-bot/src/utils/encryption.py` or decrypt tokens only when needed for container creation.

### Database Migrations
When making schema changes:
1. Create migration file with `make db-migration-create MSG="description"`
2. Test migration in development environment
3. Apply with `make db-migrate`

### Service Dependencies
- Platform Bot depends on Database and Redis
- Factory Service depends on Database and Docker socket
- Web API depends on Database
- Notification Service depends on Database and Redis
- All services depend on bot_saas_network

### Configuration Reload
Bot-template containers automatically reload configuration every 60 seconds to pick up changes from the database.
