# Database Migrations

## Overview

This directory contains database migration scripts for Telegram Bot SaaS.

## Migration Files

- `001_create_error_logs.sql` - Creates centralized error logging table
- `env.py` - Alembic environment configuration

## Running Migrations

### Initial Setup (for new database)

```bash
# Apply schema.sql
docker exec bot_saas_db_prod psql -U postgres -d bot_saas -f /docker-entrypoint-initdb.d/01-schema.sql

# Apply migrations in order
docker exec -i bot_saas_db_prod psql -U postgres -d bot_saas < migrations/001_create_error_logs.sql
```

### Development

```bash
# Using psql
psql postgresql://postgres:postgres@localhost:5432/bot_saas -f migrations/001_create_error_logs.sql

# Using Python
from database.migrations.env import run_migrations
import asyncio
asyncio.run(run_migrations())
```

## Creating New Migrations

1. Create a new SQL file with the next version number:
   ```bash
   touch migrations/002_add_new_table.sql
   ```

2. Write your migration SQL in the file.

3. Test the migration locally first.

4. Add documentation to this README.

5. Commit the migration file.

## Best Practices

- Each migration should be atomic - either fully succeed or fully fail
- Use `IF NOT EXISTS` for CREATE statements
- Use transactions for complex changes
- Add indexes for foreign keys
- Update this README with new migrations
- Test migrations on a copy of production data first

## Rollback Plan

In case a migration fails:

1. Check the error message
2. Verify the migration SQL syntax
3. Manually rollback if necessary:
   ```sql
   BEGIN;
   -- Rollback statements
   COMMIT;
   ```
4. Fix the migration script
5. Re-run the migration

## Maintenance

### Cleanup Old Logs

```bash
# Run cleanup function
docker exec bot_saas_db_prod psql -U postgres -d bot_saas -c "SELECT cleanup_old_logs();"

# Or via API
curl -X POST http://localhost:8003/api/v1/logs/cleanup
```

### Verify Schema

```bash
# List all tables
docker exec bot_saas_db_prod psql -U postgres -d bot_saas -c "\dt"

# Check indexes
docker exec bot_saas_db_prod psql -U postgres -d bot_saas -c "\di"

# Check functions
docker exec bot_saas_db_prod psql -U postgres -d bot_saas -c "\df"
```

## Troubleshooting

### Migration Already Applied

If you get "relation already exists" errors:
- Check if migration was already applied
- Use `IF NOT EXISTS` in CREATE statements
- Or manually drop and recreate (BE CAREFUL!)

### Permission Denied

Check database user permissions:
```bash
docker exec bot_saas_db_prod psql -U postgres -d bot_saas -c "\du"
```

### Lock Timeouts

For large tables, set a longer timeout:
```bash
docker exec bot_saas_db_prod psql -U postgres -d bot_saas -c "SET statement_timeout = '5min';"
```
