# 🚀 Webhook Quick Start

## Локальная разработка (Ngrok)

### 1. Запуск ngrok
```bash
cd /Users/alexsandr/Desktop/telegram-bot-saas
./scripts/setup-ngrok.sh
```

### 2. Обновление webhook для всех ботов
```bash
# Получить URL из вывода ngrok (например: https://abc123.ngrok.io)
export NGROK_WEBHOOK_URL=https://abc123.ngrok.io
python3 scripts/update-all-webhooks.py
```

### 3. Проверка
```bash
# Проверить webhook статус конкретного бота
python3 scripts/set-bot-webhook.py {BOT_TOKEN} get
```

## Продакшен (Реальный домен)

### 1. Настройка DNS
```
A запись: yourdomain.com → YOUR_SERVER_IP
```

### 2. SSL сертификат
```bash
sudo certbot certonly --standalone -d api.yourdomain.com
sudo cp /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/api.yourdomain.com/privkey.pem nginx/ssl/
```

### 3. Обновление .env
```bash
NGROK_ENABLED=false
SERVER_DOMAIN=api.yourdomain.com
WEBHOOK_BASE_URL=https://api.yourdomain.com
```

### 4. Обновление webhook
```bash
python3 scripts/update-all-webhooks.py
```

### 5. Перезапуск nginx
```bash
docker-compose restart nginx
```

## Подробная документация
Смотрите `WEBHOOK_SETUP.md` для полного руководства.

---

**Последнее обновление:** 2026-03-14
