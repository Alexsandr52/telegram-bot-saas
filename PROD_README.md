# 🚀 Telegram Bot SaaS - Production Deployment

## Quick Start

### 1. Generate Secrets
```bash
cd scripts
python3 generate-secrets.py
```

### 2. Configure Environment
```bash
cp .env.prod .env.prod.local
nano .env.prod.local
```

Update these variables:
- `SERVER_DOMAIN` - your domain name
- `PLATFORM_BOT_TOKEN` - from @BotFather
- `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `ENCRYPTION_KEY`, `JWT_SECRET_KEY` - from step 1

### 3. Deploy to VPS
```bash
./scripts/deploy-to-vps.sh
```

Or for manual deployment, see [DEPLOYMENT.md](./DEPLOYMENT.md)

## What's Included in Production Build

### Services
- ✅ PostgreSQL 15 (Database)
- ✅ Redis 7 (Cache & Queue)
- ✅ Platform Bot (Main Telegram bot)
- ✅ Factory Service (Bot container management)
- ✅ Web API (Backend)
- ✅ Web Panel (Frontend)
- ✅ Notification Service (Reminders & alerts)
- ✅ Logging Service (Centralized logging)
- ✅ Nginx (API Gateway & Reverse Proxy)
- ✅ Certbot (SSL certificate management)
- ✅ Backup Service (Automated backups)

### Security Features
- 🔒 SSL/TLS with Let's Encrypt
- 🔒 Environment variable isolation
- 🔒 No exposed internal ports
- 🔒 Health checks for all services
- 🔒 Security headers in nginx
- 🔒 Encrypted sensitive data

### Monitoring & Maintenance
- 📊 Centralized logging
- 📊 Automated daily backups
- 📊 Health check endpoints
- 📊 Service restart policies

## File Structure

```
telegram-bot-saas/
├── docker-compose.prod.yml    # Production Docker Compose
├── .env.prod                 # Production environment template
├── nginx/nginx-prod.conf     # Production nginx config
├── scripts/
│   ├── generate-secrets.py   # Generate secure secrets
│   ├── deploy-to-vps.sh      # Automatic deployment script
│   └── test-prod-locally.sh  # Test config locally
├── certbot/                  # SSL certificates (created on deploy)
├── backups/                  # Database backups
├── logs/                     # Application logs
└── bot-templates/            # Bot template configurations
```

## VPS Requirements

- **OS**: Ubuntu 20.04+ or Debian 11+
- **RAM**: 2GB minimum (4GB+ recommended)
- **CPU**: 2+ cores
- **Disk**: 20GB+ SSD
- **Domain**: A domain name pointing to VPS IP
- **Ports**: 80 & 443 must be open

## Post-Deployment

After successful deployment:

1. **Access Web Panel**: `https://yourdomain.com`
2. **Configure Bot Webhook**:
   ```bash
   curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
     -d "url=https://yourdomain.com/webhook/platform"
   ```
3. **Verify Services**:
   ```bash
   ssh root@your-vps-ip 'cd /opt/telegram-bot-saas && docker-compose ps'
   ```

## Maintenance Commands

```bash
# View logs
ssh root@your-vps-ip 'cd /opt/telegram-bot-saas && docker-compose logs -f'

# Restart services
ssh root@your-vps-ip 'cd /opt/telegram-bot-saas && docker-compose restart'

# Update application
ssh root@your-vps-ip 'cd /opt/telegram-bot-saas && docker-compose pull && docker-compose up -d'

# Manual backup
ssh root@your-vps-ip 'cd /opt/telegram-bot-saas && docker-compose exec database pg_dump -U postgres bot_saas > backup.sql'
```

## Troubleshooting

### Services not starting
```bash
ssh root@your-vps-ip 'cd /opt/telegram-bot-saas && docker-compose ps'
ssh root@your-vps-ip 'cd /opt/telegram-bot-saas && docker-compose logs [service-name]'
```

### SSL certificate issues
```bash
ssh root@your-vps-ip 'cd /opt/telegram-bot-saas && docker-compose run --rm certbot renew'
```

### High memory usage
```bash
ssh root@your-vps-ip 'docker stats'
```

## Security Checklist

- [ ] Changed all default passwords
- [ ] Generated strong encryption keys
- [ ] Configured firewall (ufw)
- [ ] Set up fail2ban
- [ ] Enabled SSH key authentication
- [ ] Configured automated off-site backups
- [ ] Set up monitoring and alerts
- [ ] Updated system regularly

## Support

For detailed information, see [DEPLOYMENT.md](./DEPLOYMENT.md)

---

**Ready to deploy! 🎉**
