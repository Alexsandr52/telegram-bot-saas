# 🚀 Telegram Bot SaaS - Deployment Guide

## Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Deploy (Automatic)](#quick-deploy-automatic)
- [Manual Deploy](#manual-deploy)
- [Post-Deployment Setup](#post-deployment-setup)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Local Machine
- SSH client installed
- Docker and Docker Compose (for local testing)
- Python 3.8+ (for secrets generation)

### VPS Requirements
- **OS**: Ubuntu 20.04+ or Debian 11+ (recommended)
- **RAM**: Minimum 2GB (4GB+ recommended)
- **CPU**: 2+ cores
- **Disk**: 20GB+ SSD
- **Domain name** pointing to VPS IP
- **Port 80 & 443 open** for web traffic

---

## Quick Deploy (Automatic)

### 1. Generate Secure Secrets

```bash
cd scripts
python3 generate-secrets.py
```

Copy the generated secrets to your `.env.prod` file.

### 2. Configure Environment

Copy and edit the environment file:

```bash
cp .env.prod .env.prod.local
nano .env.prod.local
```

**Important Variables:**
```bash
# Your domain
SERVER_DOMAIN=yourdomain.com

# Platform Bot Token (get from @BotFather)
PLATFORM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# Secure passwords (from secrets generator)
POSTGRES_PASSWORD=your_strong_password
REDIS_PASSWORD=your_strong_password
ENCRYPTION_KEY=your_encryption_key
JWT_SECRET_KEY=your_jwt_secret
```

### 3. Run Deployment Script

```bash
./scripts/deploy-to-vps.sh
```

Follow the prompts:
- Enter VPS IP/hostname
- Enter SSH username (usually `root`)
- Enter your domain name
- Enter path to .env file

The script will:
- Install Docker on VPS
- Upload all files
- Configure SSL certificates
- Start all services

---

## Manual Deploy

### 1. Connect to VPS

```bash
ssh root@your-vps-ip
```

### 2. Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker $USER

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### 3. Setup Project Directory

```bash
# Create project directory
mkdir -p /opt/telegram-bot-saas
cd /opt/telegram-bot-saas

# Create necessary directories
mkdir -p certbot/conf certbot/www
mkdir -p backups/postgres bot-templates
mkdir -p logs/{api,factory,notifications,central}
```

### 4. Upload Files

**From your local machine:**

```bash
# Use rsync to upload files
rsync -avz --delete \
  --exclude 'node_modules' \
  --exclude '__pycache__' \
  --exclude '.git' \
  . root@your-vps-ip:/opt/telegram-bot-saas/
```

Or manually copy:
- `docker-compose.prod.yml` → `docker-compose.yml`
- `.env.prod` → `.env`
- All service directories
- `nginx/` directory
- `database/` directory

### 5. Configure SSL Certificates

```bash
cd /opt/telegram-bot-saas

# Stop nginx if running
docker-compose stop nginx 2>/dev/null || true

# Get initial SSL certificates
docker run --rm \
  -v ./certbot/conf:/etc/letsencrypt \
  -v ./certbot/www:/var/www/certbot \
  certbot/certbot:latest \
  certonly --webroot -w /var/www/certbot \
  --email admin@yourdomain.com \
  --agree-tos \
  --no-eff-email \
  -d yourdomain.com

# Verify certificates
ls -la certbot/conf/live/yourdomain.com/
```

### 6. Start Services

```bash
# Build Docker images
docker-compose build

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

---

## Post-Deployment Setup

### 1. Set Platform Bot Webhook

You need to configure the Telegram bot to use webhooks:

```bash
# On VPS
docker-compose exec platform-bot python -c "
from src.bot import bot
import asyncio

async def setup_webhook():
    webhook_url = 'https://yourdomain.com/webhook/platform'
    await bot.set_webhook(webhook_url)
    print('Webhook set successfully')

asyncio.run(setup_webhook())
"
```

Or use Telegram's API directly:

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -d "url=https://yourdomain.com/webhook/platform"
```

### 2. Configure Domain in DNS

Make sure your domain points to your VPS:

```bash
# Check DNS propagation
dig yourdomain.com +short

# Should return your VPS IP
```

### 3. Test Services

```bash
# Test web panel
curl https://yourdomain.com

# Test API
curl https://yourdomain.com/health

# Test bot webhook
curl -X POST https://yourdomain.com/webhook/platform
```

### 4. Setup Monitoring

Recommended tools:
- **Uptime monitoring**: UptimeRobot, Pingdom
- **Server monitoring**: htop, glances
- **Log monitoring**: journalctl, docker logs

---

## Maintenance

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f platform-bot
docker-compose logs -f database
docker-compose logs -f nginx
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart platform-bot
```

### Update Application

```bash
# Stop services
docker-compose down

# Pull latest code
cd /opt/telegram-bot-saas
git pull  # or rsync from local

# Rebuild and start
docker-compose build
docker-compose up -d
```

### Backup Database

Automatic backups are configured, but you can also backup manually:

```bash
# Manual backup
docker-compose exec database pg_dump -U postgres bot_saas > backup_$(date +%Y%m%d).sql

# Restore from backup
docker-compose exec -T database psql -U postgres bot_saas < backup_file.sql
```

### Cleanup Old Data

```bash
# Cleanup unused Docker images
docker system prune -a

# Cleanup old volumes
docker volume prune

# Cleanup old backups (keep last 7 days)
find backups/postgres -name "*.sql" -mtime +7 -delete
```

---

## Troubleshooting

### Services Won't Start

```bash
# Check service status
docker-compose ps

# Check logs
docker-compose logs [service-name]

# Common issues:
# 1. Port conflicts - Check if ports are already in use
# 2. Database connection - Check if database is healthy
# 3. Missing environment variables - Check .env file
```

### SSL Certificate Issues

```bash
# Renew certificates manually
docker-compose run --rm certbot renew

# Check certificate status
docker-compose run --rm certbot certificates

# Force renewal
docker-compose run --rm certbot renew --force-renewal
```

### Bot Not Responding

```bash
# Check if bot is running
docker-compose ps platform-bot

# Check bot logs
docker-compose logs -f platform-bot

# Verify webhook
curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo

# Remove webhook (to switch to polling)
curl https://api.telegram.org/bot<TOKEN>/deleteWebhook
```

### High Memory Usage

```bash
# Check system resources
free -h
df -h
docker stats

# Restart heavy services
docker-compose restart factory-service
```

### Database Connection Issues

```bash
# Check database health
docker-compose exec database pg_isready -U postgres

# Connect to database
docker-compose exec database psql -U postgres -d bot_saas

# Check active connections
docker-compose exec database psql -U postgres -d bot_saas -c "SELECT count(*) FROM pg_stat_activity;"
```

---

## Security Best Practices

1. **Change default passwords** in `.env` file
2. **Keep system updated** (`apt update && apt upgrade`)
3. **Use strong SSH keys** instead of passwords
4. **Configure firewall** (ufw)
5. **Enable fail2ban** to prevent brute force attacks
6. **Regular backups** to external location
7. **Monitor logs** for suspicious activity

### Configure Firewall

```bash
# Install ufw
apt install ufw

# Allow SSH
ufw allow 22/tcp

# Allow HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Enable firewall
ufw enable

# Check status
ufw status
```

---

## Support

For issues and questions:
- Check logs: `docker-compose logs -f`
- Review this documentation
- Check service status: `docker-compose ps`
- Verify environment variables in `.env` file

---

## Next Steps

After successful deployment:

1. ✅ Configure your platform bot
2. ✅ Test the web panel at `https://yourdomain.com`
3. ✅ Create your first bot
4. ✅ Set up monitoring and alerts
5. ✅ Configure automated off-site backups
6. ✅ Document your custom configurations

---

**Enjoy your Telegram Bot SaaS platform! 🎉**
