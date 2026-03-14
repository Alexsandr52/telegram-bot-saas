# Webhook Setup Guide

## Overview
Telegram Bot SaaS supports webhooks for real-time message delivery. You can use:
- **ngrok** - for local development
- **Real domain** - for production deployment

---

## 🔄 Option 1: Local Development with ngrok

### Prerequisites
1. Install ngrok: `brew install ngrok` (macOS) or download from https://ngrok.com
2. Get ngrok authtoken: https://dashboard.ngrok.com/get-started/your-authtoken

### Setup Steps

#### 1. Configure Environment

Create/update `.env` file:

```bash
# Enable ngrok
NGROK_ENABLED=true
NGROK_AUTH_TOKEN=your_ngrok_auth_token_here
NGROK_DOMAIN=  # Leave empty for random domain

# For local development
SERVER_DOMAIN=localhost
```

#### 2. Start Ngrok

```bash
# Make script executable
chmod +x scripts/setup-ngrok.sh

# Run ngrok setup
./scripts/setup-ngrok.sh
```

This will:
- Install ngrok if needed
- Start ngrok tunnel on port 80
- Display webhook URL (e.g., `https://abc123.ngrok.io`)
- Open ngrok dashboard at `http://localhost:4040`

#### 3. Start Services

```bash
# Start all services
docker-compose up -d

# Check services
docker-compose ps
```

#### 4. Set Webhook for Bot

```bash
# Make script executable
chmod +x scripts/set-bot-webhook.py

# Set webhook (example)
python3 scripts/set-bot-webhook.py \
    123456789:ABCdefGHIjklMNOpqrsTUVwxyz \
    set \
    --webhook-url https://abc123.ngrok.io/webhook/{bot_id} \
    --secret-token your_secret_here

# Check webhook status
python3 scripts/set-bot-webhook.py 123456789:ABCdefGHIjklMNOpqrsTUVwxyz get
```

#### 5. Test Webhook

```bash
# Check bot logs
docker logs bot_74702bd7 -f

# Check ngrok logs
# Visit http://localhost:4040/inspect/http to see webhook requests
```

### Ngrok Tips

- **Random domain**: ngrok generates random URL each time
- **Custom domain**: You can set custom subdomain with paid plan
- **Session persistence**: ngrok URL changes on restart (consider paid plan)
- **Rate limits**: Free tier has rate limits (~40 connections/minute)

---

## 🌐 Option 2: Production with Real Domain

### Prerequisites
1. Purchased domain (e.g., `yourdomain.com`)
2. DNS configured to point to your server IP
3. SSL certificate (Let's Encrypt or commercial)

### Setup Steps

#### 1. Configure DNS

```
Type: A
Name: @ (or your subdomain, e.g., api)
Value: YOUR_SERVER_IP
TTL: 300 (or default)
```

#### 2. Obtain SSL Certificate

**Option A: Let's Encrypt (Free)**

```bash
# Install certbot
sudo apt-get install certbot

# Get certificate
sudo certbot certonly --standalone \
    -d api.yourdomain.com \
    --email your@email.com \
    --agree-tos \
    --non-interactive

# Copy certificates to project
sudo cp /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem nginx/ssl/fullchain.pem
sudo cp /etc/letsencrypt/live/api.yourdomain.com/privkey.pem nginx/ssl/privkey.pem
```

**Option B: Commercial Certificate**

Place your certificates in `nginx/ssl/`:
- `fullchain.pem` (certificate + chain)
- `privkey.pem` (private key)

#### 3. Configure Environment

Update `.env` file:

```bash
# Production domain
SERVER_DOMAIN=api.yourdomain.com

# SSL certificates
SSL_CERT_PATH=/etc/nginx/ssl/fullchain.pem
SSL_KEY_PATH=/etc/nginx/ssl/privkey.pem

# Webhook base URL
WEBHOOK_BASE_URL=https://api.yourdomain.com

# Disable ngrok
NGROK_ENABLED=false
```

#### 4. Update Docker Compose

Ensure nginx uses webhook config:

```yaml
nginx:
  volumes:
    - ./nginx/nginx-webhook.conf:/etc/nginx/nginx.conf:ro  # Use webhook config
    - ./nginx/ssl:/etc/nginx/ssl:ro
```

#### 5. Start Services

```bash
# Start services
docker-compose up -d

# Check nginx is listening
netstat -tlnp | grep :80
netstat -tlnp | grep :443
```

#### 6. Set Webhook for Bot

```bash
python3 scripts/set-bot-webhook.py \
    123456789:ABCdefGHIjklMNOpqrsTUVwxyz \
    set \
    --webhook-url https://api.yourdomain.com/webhook/{bot_id} \
    --secret-token your_secret_here
```

#### 7. Verify Webhook

```bash
# Check webhook info
python3 scripts/set-bot-webhook.py 123456789:ABCdefGHIjklMNOpqrsTUVwxyz get

# Should show:
# URL: https://api.yourdomain.com/webhook/{bot_id}
# Pending update count: 0
```

#### 8. Test Webhook

```bash
# Test webhook manually
curl -X POST https://api.yourdomain.com/webhook/{bot_id} \
    -H "Content-Type: application/json" \
    -d '{"test": true}'

# Check bot logs
docker logs bot_74702bd7 -f

# Check nginx logs
docker logs bot_saas_nginx -f
```

---

## 🔧 Webhook URL Format

### Development (ngrok)
```
https://{random_subdomain}.ngrok.io/webhook/{bot_id}
```

Example: `https://abc123xyz.ngrok.io/webhook/74702bd7-8a8c-4b9e-94d6-713059abaf6e`

### Production
```
https://{your_domain}/webhook/{bot_id}
```

Example: `https://api.yourdomain.com/webhook/74702bd7-8a8c-4b9e-94d6-713059abaf6e`

---

## 🔒 Security

### Secret Token

Always use a secret token for webhook security:

```bash
python3 scripts/set-bot-webhook.py \
    {bot_token} \
    set \
    --webhook-url {webhook_url} \
    --secret-token "random_secret_string_here"
```

The bot will validate this token in incoming webhook requests.

### Firewall Rules

Ensure these ports are open:
- **Port 80** (HTTP)
- **Port 443** (HTTPS)

```bash
# Ubuntu/Debian
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --reload
```

---

## 🐛 Troubleshooting

### Issue: Webhook not receiving updates

**Symptoms**: No updates in bot logs, webhook shows no traffic

**Solutions**:
1. Verify webhook is set: `python3 scripts/set-bot-webhook.py {token} get`
2. Check ngrok is running: Visit `http://localhost:4040`
3. Test webhook manually with curl
4. Check firewall rules

### Issue: Webhook returns 404

**Symptoms**: Telegram returns webhook error 404

**Solutions**:
1. Verify nginx is using `nginx-webhook.conf`
2. Check bot_id in URL matches actual bot UUID
3. Restart nginx: `docker-compose restart nginx`

### Issue: Webhook returns 500

**Symptoms**: Telegram returns webhook error 500

**Solutions**:
1. Check bot logs: `docker logs bot_74702bd7`
2. Check bot is running: `docker ps | grep bot_`
3. Verify bot can connect to database
4. Check nginx logs: `docker logs bot_saas_nginx`

### Issue: Ngrok URL changes

**Symptoms**: Webhook stops working after ngrok restart

**Solutions**:
1. Update webhook with new ngrok URL
2. Consider ngrok paid plan for fixed domain
3. Use `--domain` flag for reserved domain (paid)

### Issue: SSL Certificate Error

**Symptoms**: Webhook setup fails with SSL error

**Solutions**:
1. Verify certificate chain is correct (`fullchain.pem`)
2. Check certificate is not expired
3. Use Let's Encrypt staging for testing
4. Verify nginx SSL configuration

---

## 📝 Automatic Webhook Setup

### Factory Service Integration

The factory service can automatically set webhooks when creating bots:

```python
# In factory service
async def create_bot_with_webhook(bot_id, bot_token):
    webhook_url = os.getenv("WEBHOOK_BASE_URL")
    if webhook_url:
        full_url = f"{webhook_url}/webhook/{bot_id}"
        await set_telegram_webhook(bot_token, full_url)
```

### Platform Bot Integration

Add webhook setup to bot creation flow:

```python
# In platform bot
async def on_bot_created(bot_id, bot_token):
    webhook_url = get_webhook_base_url()
    await set_telegram_webhook(bot_token, f"{webhook_url}/webhook/{bot_id}")
```

---

## 🔄 Switching Between Modes

### From ngrok to Production

```bash
# Stop services
docker-compose down

# Update .env
NGROK_ENABLED=false
SERVER_DOMAIN=api.yourdomain.com

# Set webhook to production URL
python3 scripts/set-bot-webhook.py {token} set --webhook-url https://api.yourdomain.com/webhook/{bot_id}

# Start services
docker-compose up -d
```

### From Production to ngrok

```bash
# Stop services
docker-compose down

# Update .env
NGROK_ENABLED=true
SERVER_DOMAIN=localhost

# Start ngrok
./scripts/setup-ngrok.sh &

# Set webhook to ngrok URL
python3 scripts/set-bot-webhook.py {token} set --webhook-url https://abc123.ngrok.io/webhook/{bot_id}

# Start services
docker-compose up -d
```

---

## 📊 Monitoring

### Webhook Metrics

Monitor webhook activity:

```bash
# Check nginx status
curl http://localhost/nginx_status

# Check webhook traffic
docker logs bot_saas_nginx | grep "POST /webhook/"

# Check bot webhook handler logs
docker logs bot_74702bd7 | grep "Webhook update"
```

### Telegram Bot API Info

Check webhook info via Telegram API:

```bash
curl https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo
```

---

## 🎯 Best Practices

1. **Always use HTTPS** for production webhooks
2. **Set secret token** for webhook security
3. **Monitor webhook failures** with logs and metrics
4. **Have fallback plan** (polling) for critical systems
5. **Test webhooks** thoroughly before production
6. **Use proper SSL certificates** from trusted CA
7. **Keep webhook URLs stable** to avoid setup issues
8. **Implement retry logic** for failed webhook deliveries
9. **Monitor rate limits** on webhook endpoints
10. **Document webhook endpoints** for team reference

---

## 📞 Support

For issues:
- Check logs: `docker logs {container_name}`
- Verify configuration: `cat .env`
- Test webhook manually with curl
- Check Telegram API status: https://core.telegram.org/bots/api#getting-updates

---

**Last Updated:** 2026-03-14
**Version:** 1.0
