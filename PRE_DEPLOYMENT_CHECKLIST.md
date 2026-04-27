# ✅ Pre-Deployment Checklist

## Critical Requirements (MUST complete before deployment)

### 1. 🔐 Security & Secrets
- [ ] **Generate strong passwords** - Run `./scripts/generate-secrets.sh`
- [ ] **Update .env.prod** with all generated secrets:
  - [ ] `ENCRYPTION_KEY` - Fernet key from cryptography
  - [ ] `JWT_SECRET_KEY` - URL-safe token
  - [ ] `POSTGRES_PASSWORD` - Strong password (32+ chars)
  - [ ] `REDIS_PASSWORD` - Strong password (32+ chars)
  - [ ] `PLATFORM_BOT_WEBHOOK_SECRET` - Strong secret (32+ chars)
- [ ] **Get Telegram Bot Token** - From @BotFather
- [ ] **Configure proxy for Russia** - Add `TELEGRAM_PROXY` to .env.prod
- [ ] **Remove all default values** - No "CHANGE_THIS" in .env.prod

### 2. 🌐 Domain & DNS
- [ ] **Domain purchased** - Own domain name
- [ ] **DNS configured** - A record pointing to VPS IP
- [ ] **DNS propagated** - Wait 24-48 hours, verify with `dig yourdomain.com`
- [ ] **Server DOMAIN updated** - Update `SERVER_DOMAIN` in .env.prod
- [ ] **Webhook URL set** - Update `WEBHOOK_BASE_URL` in .env.prod
- [ ] **CORS configured** - Add domain to `CORS_ORIGINS` in .env.prod

### 3. 🔧 Server Configuration
- [ ] **VPS ready** - Minimum 2 vCPU, 8GB RAM, 50GB disk
- [ ] **OS compatible** - Ubuntu 22.04 LTS or Debian 12
- [ ] **Docker installed** - Version 24+
- [ ] **Docker Compose installed** - Plugin available
- [ ] **User in docker group** - `sudo usermod -aG docker $USER`
- [ ] **Project cloned/uploaded** - Files in `/opt/telegram-bot-saas`
- [ ] **Directories created**:
  - [ ] `certbot/conf/`
  - [ ] `certbot/www/`
  - [ ] `backups/postgres/`
  - [ ] `logs/platform-bot/`
  - [ ] `logs/factory/`
  - [ ] `logs/api/`
  - [ ] `logs/notifications/`

### 4. 🔒 SSL Certificates
- [ ] **Port 80 open** - Firewall allows HTTP
- [ ] **Port 443 open** - Firewall allows HTTPS
- [ ] **Nginx configured** - nginx-prod.conf set up correctly
- [ ] **Certbot ready** - certbot service in docker-compose.prod.yml
- [ ] **Obtain certificate** - Run after deployment:
  ```bash
  docker compose -f docker-compose.prod.yml run --rm certbot certonly \
    --webroot -w /var/www/certbot -d yourdomain.com
  ```

### 5. 🗄️ Database
- [ ] **Schema applied** - Run `./scripts/run-migrations.sh --init`
- [ ] **Migrations applied** - Run `./scripts/run-migrations.sh`
- [ ] **Partitions created** - Current year partitions exist (2026)
- [ ] **Indexes created** - All foreign key indexes present
- [ ] **Connection pooling configured** - Check pool sizes in config
- [ ] **Error logging table** - `error_logs` table exists

### 6. 🤖 Telegram Bot
- [ ] **Bot created via @BotFather**
- [ ] **Token saved securely**
- [ ] **Webhook mode enabled** - `BOT_WEBHOOK_MODE=true` in .env.prod
- [ ] **Proxy configured** - `TELEGRAM_PROXY` set (critical for Russia!)
- [ ] **Webhook path set** - `BOT_WEBHOOK_PATH` configured

### 7. 📊 Monitoring & Logging
- [ ] **Health checks enabled** - All services have health endpoints
- [ ] **Metrics configured** - Prometheus metrics exported
- [ ] **Rate limiting enabled** - nginx has rate limiting zones
- [ ] **Log rotation configured** - Docker log limits set
- [ ] **Alerts configured** - Sentry DSN set or local alerts
- [ ] **Monitoring stack ready** - Prometheus + Grafana optional but recommended

### 8. 💾 Backups & Recovery
- [ ] **Backup script tested** - `./scripts/backup-db.sh` works
- [ ] **Restore script tested** - `./scripts/restore-db.sh --list` works
- [ ] **Backup directory exists** - `backups/postgres/` created
- [ ] **Retention policy set** - Days, weeks, months configured
- [ ] **Backup automation** - Docker backup service or cron job configured
- [ ] **Test restore performed** - Restore from backup works

### 9. 🔥 Firewall & Security
- [ ] **UFW enabled** - Firewall configured
- [ ] **SSH port open** - Port 22 open (or restricted)
- [ ] **HTTP port open** - Port 80 open
- [ ] **HTTPS port open** - Port 443 open
- [ ] **Other ports closed** - Only necessary ports open
- [ ] **Fail2Ban enabled** - Brute force protection active
- [ ] **Root login disabled** - SSH root login disabled
- [ ] **SSH keys only** - Password auth disabled
- [ ] **System updated** - `apt update && apt upgrade -y`

### 10. 🚀 Application Configuration
- [ ] **Platform bot config** - All environment variables set
- [ ] **Factory service config** - Docker socket access configured
- [ ] **Web API config** - CORS and JWT configured
- [ ] **Notification service config** - Redis and database connected
- [ ] **Logging service config** - Database URL configured
- [ ] **Nginx config** - All upstreams and routes correct
- [ ] **Port conflicts checked** - No port conflicts
- [ ] **Memory limits set** - Container memory limits configured

## Testing Requirements (Test locally first!)

### 1. Local Testing
- [ ] **Docker build succeeds** - `docker compose -f docker-compose.yml build`
- [ ] **Services start locally** - `docker compose -f docker-compose.yml up -d`
- [ ] **All containers healthy** - `docker ps` shows all services Up/healthy
- [ ] **Platform bot works** - Bot responds to /start
- [ ] **Web panel accessible** - Can login at http://localhost:3000
- [ ] **API responding** - `curl http://localhost:8000/health`
- [ ] **Factory service works** - `curl http://localhost:8002/api/v1/health`
- [ ] **Database accessible** - Can connect to PostgreSQL
- [ ] **Redis accessible** - Can connect to Redis

### 2. Proxy Testing (Critical for Russia)
- [ ] **Proxy server acquired** - Working SOCKS5 proxy
- [ ] **Proxy configured locally** - `TELEGRAM_PROXY` set
- [ ] **Bot works via proxy** - Bot receives updates via proxy
- [ ] **Webhook works via proxy** - Telegram can reach webhook

## Pre-Deployment Validation

### Final Checks (Must pass all)

```bash
# 1. Validate environment variables
cd /opt/telegram-bot-saas
cat .env.prod | grep "CHANGE_THIS"  # Should return empty

# 2. Test database connection
docker compose -f docker-compose.prod.yml run --rm database \
  psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 1;"

# 3. Test Docker socket access
docker ps  # Should work without sudo

# 4. Check available disk space
df -h  # Should have >20% free space

# 5. Check available memory
free -h  # Should have enough RAM

# 6. Test proxy connectivity
curl -x $TELEGRAM_PROXY https://api.telegram.org

# 7. Verify DNS propagation
dig +short yourdomain.com

# 8. Test SSL (after deployment)
openssl s_client -servername yourdomain.com -connect yourdomain.com:443
```

## Deployment Process

### Step-by-Step Deployment

1. **Upload project to server**
   ```bash
   rsync -avz ./ user@server:/opt/telegram-bot-saas/
   # or
   git clone <repo-url> /opt/telegram-bot-saas
   ```

2. **Configure environment**
   ```bash
   cd /opt/telegram-bot-saas
   ./scripts/generate-secrets.sh
   nano .env.prod  # Update with real values
   ```

3. **Build images**
   ```bash
   docker compose -f docker-compose.prod.yml build --no-cache
   ```

4. **Start database**
   ```bash
   docker compose -f docker-compose.prod.yml up -d database redis
   sleep 10  # Wait for database to be ready
   ```

5. **Run migrations**
   ```bash
   ./scripts/run-migrations.sh --init
   ./scripts/run-migrations.sh
   ```

6. **Start all services**
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```

7. **Verify services**
   ```bash
   docker compose -f docker-compose.prod.yml ps
   docker logs platform-bot --tail=50
   ```

8. **Obtain SSL certificate**
   ```bash
   docker compose -f docker-compose.prod.yml run --rm certbot certonly \
     --webroot -w /var/www/certbot -d yourdomain.com
   ```

9. **Configure webhook**
   ```bash
   ./scripts/setup-webhooks.sh
   ```

10. **Test everything**
    ```bash
    # Test health endpoints
    curl https://yourdomain.com/health
    curl https://yourdomain.com/api/health

    # Test bot in Telegram
    # Open bot and send /start

    # Test web panel
    # Open https://yourdomain.com

    # Test webhook
    curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
    ```

11. **Create first backup**
    ```bash
    ./scripts/backup-db.sh
    ```

## Post-Deployment Verification

### Must verify within 1 hour
- [ ] All containers show "Up" status
- [ ] All health checks return "healthy"
- [ ] Platform bot receives messages
- [ ] Web panel loads correctly
- [ ] Can create new bot
- [ ] Webhooks receive updates
- [ ] No errors in logs (check all services)
- [ ] SSL certificate is valid
- [ ] Rate limiting works (test with multiple requests)

### Must verify within 24 hours
- [ ] Backup was created successfully
- [ ] Monitoring is collecting metrics
- [ ] Alerts are working (if configured)
- [ ] No resource exhaustion (CPU/RAM/disk)
- [ ] All services auto-restart on failure

## Emergency Rollback Plan

If deployment fails, rollback steps:

1. **Stop all services**
   ```bash
   docker compose -f docker-compose.prod.yml down
   ```

2. **Restore database from backup**
   ```bash
   ./scripts/restore-db.sh --latest-daily
   ```

3. **Restart services**
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```

4. **Verify functionality**
   ```bash
   docker compose -f docker-compose.prod.yml ps
   docker logs platform-bot --tail=50
   ```

## Common Issues & Solutions

### Issue: Telegram not working
**Solution:** Check proxy configuration in .env.prod
```bash
TELEGRAM_PROXY=socks5://user:pass@host:port
```

### Issue: Webhook not receiving updates
**Solution:** Check SSL certificate and DNS
```bash
openssl s_client -servername yourdomain.com -connect yourdomain.com:443
dig yourdomain.com
```

### Issue: Container restarting
**Solution:** Check logs and environment variables
```bash
docker logs <container_name> --tail=100
docker inspect <container_name> | grep -A 20 Env
```

### Issue: Out of memory
**Solution:** Add swap or reduce bot count
```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Issue: Database connection failed
**Solution:** Check database is running and URL is correct
```bash
docker ps | grep database
docker compose -f docker-compose.prod.yml logs database
```

## Documentation Reference

- `DEPLOYMENT.md` - Full deployment guide
- `DEPLOYMENT_CHECKLIST.md` - Detailed checklist (deprecated)
- `DEPLOYMENT_PLAN.md` - Step-by-step deployment plan
- `MONITORING_SETUP.md` - Monitoring configuration
- `PRODUCTION_TROUBLESHOOTING.md` - Troubleshooting guide
- `scripts/README.md` - Scripts documentation

## Success Criteria

Deployment is successful when:

- ✅ All critical requirements checked above
- ✅ All containers healthy
- ✅ Platform bot responds
- ✅ Web panel accessible
- ✅ Webhooks working
- ✅ SSL certificate valid
- ✅ Proxy configured (for Russia)
- ✅ Backups working
- ✅ No critical errors
- ✅ Resources within limits

## Final Reminder

**DO NOT deploy without:**
1. Strong passwords generated
2. Proxy configured (Russia!)
3. SSL certificate obtained
4. Backups tested
5. All health checks passing

**ALWAYS:**
1. Test locally first
2. Use staging server if available
3. Have rollback plan ready
4. Monitor closely for 24 hours
5. Document all changes

**Good luck with deployment! 🚀**
