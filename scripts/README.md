# Telegram Bot SaaS - Deployment Scripts

This directory contains scripts for deployment and maintenance of the Telegram Bot SaaS platform.

## Scripts Overview

### 🔄 Setup & Configuration

#### `setup-webhooks.sh`
Configures Telegram webhook for the platform bot.

**Usage:**
```bash
cd scripts
./setup-webhooks.sh
```

**Features:**
- Checks SSL certificate validity
- Tests webhook URL reachability
- Sets webhook with secret token
- Displays current webhook information
- Deletes webhook if needed

**Requirements:**
- `curl` installed
- `python3` installed (for JSON parsing)
- `openssl` installed (for SSL check)
- `.env` or `.env.prod` file with:
  - `WEBHOOK_BASE_URL` - Full webhook URL (e.g., https://yourdomain.com)
  - `PLATFORM_BOT_WEBHOOK_SECRET` - Secret token for webhook validation
  - `PLATFORM_BOT_TOKEN` - Telegram bot token

### 💾 Backups

#### `backups/backup-db.sh`
Automated database backup script.

**Usage:**
```bash
cd scripts/backups
./backup-db.sh
```

**Features:**
- Daily backups (every day)
- Weekly backups (Sundays)
- Monthly backups (1st of month)
- Automatic cleanup based on retention policy
- Compressed backups (.sql.gz)

**Backup Locations:**
- `backups/postgres/daily/` - Daily backups (kept for 30 days by default)
- `backups/postgres/weekly/` - Weekly backups (kept for 8 weeks by default)
- `backups/postgres/monthly/` - Monthly backups (kept for 6 months by default)

**Configuration (.env):**
```bash
BACKUP_DIR=/var/backups/bot-saas           # Directory for backups
BACKUP_RETENTION_DAYS=30                     # Daily backup retention
BACKUP_RETENTION_WEEKS=8                      # Weekly backup retention
BACKUP_RETENTION_MONTHS=6                     # Monthly backup retention
```

#### `backups/restore-db.sh`
Database restore script.

**Usage:**
```bash
cd scripts/backups

# List available backups
./restore-db.sh --list

# Restore specific backup
./restore-db.sh /var/backups/bot-saas/daily/backup_20250321_120000.sql.gz

# Restore latest daily backup
./restore-db.sh --latest daily
```

**Features:**
- List all available backups
- Restore from specific backup file
- Restore latest backup by type (daily/weekly/monthly)
- Confirmation prompt before restore
- Automatic decompression and restore

**⚠️ Warning:** This will REPLACE the current database!

### 📋 Maintenance

#### `webhook-tester.py`
Script to test webhook functionality (in development).

**Usage:**
```bash
cd scripts
python webhook-tester.py
```

---

## Deployment Checklist

Use this checklist when deploying to production:

### 1. Initial Setup
- [ ] Copy `.env.example` to `.env.prod`
- [ ] Update all passwords and secrets in `.env.prod`
- [ ] Generate strong `ENCRYPTION_KEY` and `JWT_SECRET_KEY`
- [ ] Update `WEBHOOK_BASE_URL` with your domain
- [ ] Update `SERVER_DOMAIN` with your domain
- [ ] Update `CORS_ORIGINS` with your domain
- [ ] Get `PLATFORM_BOT_TOKEN` from @BotFather
- [ ] Create backup directory: `mkdir -p backups/postgres`

### 2. Database & Redis
- [ ] Check PostgreSQL health: `docker compose -f docker-compose.prod.yml ps database`
- [ ] Check Redis health: `docker compose -f docker-compose.prod.yml ps redis`
- [ ] Verify database schema is applied

### 3. Webhooks
- [ ] Run webhook setup: `./scripts/setup-webhooks.sh`
- [ ] Verify SSL certificate is valid
- [ ] Verify webhook URL is accessible
- [ ] Test webhook with Telegram API

### 4. Backups
- [ ] Verify backup directory exists
- [ ] Run manual backup test: `./scripts/backups/backup-db.sh`
- [ ] Verify backup files are created
- [ ] Set up cron job or use docker-compose backup service

### 5. Services
- [ ] Check all services are running: `docker compose -f docker-compose.prod.yml ps`
- [ ] Check health endpoints:
  - `curl http://localhost:8000/health` (web-api)
  - `curl http://localhost:8001/health` (factory-service)
  - `curl http://localhost:8001/health` (logging-service)
- [ ] Test platform bot in Telegram
- [ ] Test web panel: `https://yourdomain.com`
- [ ] Test factory service API

### 6. Monitoring
- [ ] Set up log monitoring
- [ ] Configure alerts for service failures
- [ ] Set up disk space monitoring
- [ ] Set up database backup monitoring

### 7. Security
- [ ] Change all default passwords
- [ ] Enable firewall (ufw)
- [ ] Configure rate limiting in nginx
- [ ] Set up fail2ban
- [ ] Restrict SSH access
- [ ] Update system packages: `apt update && apt upgrade -y`

---

## Troubleshooting

### Webhook not working
1. Check webhook URL is correct in `.env.prod`
2. Verify SSL certificate is valid
3. Check nginx configuration
4. Check port 443 is open: `sudo ufw status`
5. Check webhook info: `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo`

### Backup not creating
1. Check backup directory exists
2. Check database is running
3. Check disk space: `df -h`
4. Check backup script permissions: `ls -l scripts/backups/`

### Service not starting
1. Check logs: `docker logs -f <service_name>`
2. Check database connectivity
3. Check environment variables
4. Check port conflicts

---

## Cron Jobs (Optional)

If you prefer cron jobs over docker-compose backup service:

```bash
# Edit crontab
crontab -e

# Add daily backup at 3 AM
0 3 * * * cd /path/to/telegram-bot-saas/scripts/backups && ./backup-db.sh >> /var/log/backup.log 2>&1

# Add backup cleanup weekly
0 4 * * 0 cd /path/to/telegram-bot-saas/scripts/backups && ./backup-db.sh >> /var/log/backup.log 2>&1
```

---

## Support

For issues or questions:
1. Check service logs: `docker logs -f <service_name>`
2. Check deployment documentation: `../DEPLOYMENT.md`
3. Check development documentation: `../DEVELOPMENT.md`
