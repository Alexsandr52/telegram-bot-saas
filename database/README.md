# Database Documentation

## Overview

This directory contains the database schema, migrations, and initialization scripts for the Telegram Bot SaaS platform.

## Structure

```
database/
├── README.md              # This file
├── schema.sql             # Complete database schema
├── alembic.ini            # Alembic configuration
├── init/                  # Initialization scripts
│   ├── 00-init.sh        # Main init script
│   └── 99-seed-data.sql  # Example seed data
└── migrations/            # Alembic migrations
    ├── env.py            # Environment configuration
    ├── script.py.mako    # Migration template
    └── versions/         # Migration files
```

## Quick Start

### 1. Start Database with Docker

```bash
# Copy environment variables
cp ../.env.example ../.env

# Start PostgreSQL, Redis, and admin tools
docker-compose up -d

# Check logs
docker-compose logs -f database
```

### 2. Access Database

#### Using psql (CLI)
```bash
docker-compose exec database psql -U postgres -d bot_saas
```

#### Using pgAdmin (Web UI)
1. Open http://localhost:5050
2. Login with credentials from `.env`
3. Add server: `database:5432`

#### Using Redis Commander
1. Open http://localhost:8082
2. Browse Redis data

## Database Schema

### Core Tables

| Table | Description |
|-------|-------------|
| `masters` | Platform users (masters) |
| `bots` | Master's Telegram bots |
| `clients` | Customer records |
| `services` | Services offered by masters |
| `appointments` | Booking records |
| `schedules` | Working hours |
| `subscriptions` | Tariff plans |
| `payments` | Payment records |
| `notifications_queue` | Notification queue |

### Views

- `active_subscriptions_view` - Active subscriptions with bot count
- `today_appointments_view` - Today's appointments across all bots
- `bot_statistics_view` - Statistics per bot

## Database Functions

### `check_slot_availability(bot_id, start_time, end_time)`
Check if a time slot is available for booking.

```sql
SELECT check_slot_availability(
    'bot-uuid'::UUID,
    '2025-01-15 10:00:00'::TIMESTAMPTZ,
    '2025-01-15 11:00:00'::TIMESTAMPTZ
);
```

### `get_available_slots(bot_id, date, service_id)`
Get available time slots for a specific date.

```sql
SELECT * FROM get_available_slots(
    'bot-uuid'::UUID,
    '2025-01-15'::DATE,
    'service-uuid'::UUID
);
```

### `cleanup_old_logs()`
Delete system logs older than 30 days.

```sql
SELECT cleanup_old_logs();
```

## Migrations (Alembic)

### Create a New Migration

```bash
# From project root
cd database

# Create migration (autogenerate)
alembic revision --autogenerate -m "Description of changes"

# Create empty migration
alembic revision -m "Description"
```

### Apply Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade to specific version
alembic upgrade +1

# Downgrade one version
alembic downgrade -1

# Downgrade to base
alembic downgrade base
```

### View Migration History

```bash
# Show current version
alembic current

# Show all versions
alembic history
```

## Backup & Restore

### Backup Database

```bash
# Backup to file
docker-compose exec database pg_dump -U postgres bot_saas > backup_$(date +%Y%m%d).sql

# Backup with gzip
docker-compose exec database pg_dump -U postgres bot_saas | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Restore Database

```bash
# Restore from file
docker-compose exec -T database psql -U postgres bot_saas < backup_20250115.sql

# Restore from gzip
gunzip -c backup_20250115.sql.gz | docker-compose exec -T database psql -U postgres bot_saas
```

## Monitoring

### Check Database Size

```sql
SELECT
    pg_database.datname,
    pg_size_pretty(pg_database_size(pg_database.datname)) AS size
FROM pg_database
WHERE datname = 'bot_saas';
```

### Check Table Sizes

```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Check Active Connections

```sql
SELECT
    count(*) as connections,
    state
FROM pg_stat_activity
WHERE datname = 'bot_saas'
GROUP BY state;
```

## Common Queries

### Get All Appointments for a Bot

```sql
SELECT
    a.id,
    a.start_time,
    a.status,
    c.first_name,
    c.last_name,
    c.phone,
    s.name as service_name
FROM appointments a
JOIN clients c ON c.id = a.client_id
JOIN services s ON s.id = a.service_id
WHERE a.bot_id = 'your-bot-uuid'
ORDER BY a.start_time DESC;
```

### Get Today's Revenue for a Bot

```sql
SELECT
    COALESCE(SUM(price), 0) as revenue,
    COUNT(*) as completed_appointments
FROM appointments
WHERE bot_id = 'your-bot-uuid'
    AND status = 'completed'
    AND DATE(start_time) = CURRENT_DATE;
```

### Get Client Statistics

```sql
SELECT
    c.first_name,
    c.last_name,
    c.phone,
    c.total_visits,
    c.total_spent,
    COUNT(a.id) as upcoming_appointments
FROM clients c
LEFT JOIN appointments a ON c.id = a.client_id AND a.start_time > NOW()
WHERE c.bot_id = 'your-bot-uuid'
GROUP BY c.id
ORDER BY c.total_spent DESC;
```

## Troubleshooting

### Database Won't Start

```bash
# Check logs
docker-compose logs database

# Remove volumes and restart (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d
```

### Connection Refused

```bash
# Check if database is running
docker-compose ps

# Check port is available
lsof -i :5432

# Verify environment variables
docker-compose config | grep POSTGRES
```

### Reset Database

```bash
# Stop containers
docker-compose down

# Remove volumes
docker volume rm bot_saas_postgres_data

# Restart
docker-compose up -d
```

## Security Notes

⚠️ **Important Security Considerations:**

1. **Never commit `.env` file** - use `.env.example` as template
2. **Encrypt bot tokens** before storing in database
3. **Use strong passwords** in production
4. **Enable SSL** for database connections in production
5. **Regular backups** - set up automated backups
6. **Limit network access** - don't expose ports in production
7. **Use read replicas** for scaling read operations

## Performance Tips

1. **Use indexes** - already created for common queries
2. **Partition large tables** - analytics_events is partitioned by month
3. **Vacuum regularly** - PostgreSQL autovacuum is enabled
4. **Monitor slow queries** - check pg_stat_statements
5. **Use connection pooling** - consider PgBouncer for production
6. **Cache frequently accessed data** - use Redis for caching

## Next Steps

- [ ] Set up automated backups
- [ ] Configure monitoring (Prometheus + Grafana)
- [ ] Set up read replicas for scaling
- [ ] Configure connection pooling
- [ ] Enable query logging for development
- [ ] Set up SSL for production
- [ ] Create database user with limited privileges
- [ ] Set up log rotation

## Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Docker PostgreSQL](https://hub.docker.com/_/postgres)
- [pgAdmin Documentation](https://www.pgadmin.org/docs/)
