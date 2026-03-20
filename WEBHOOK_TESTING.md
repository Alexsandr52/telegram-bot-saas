# 🎯 Webhook Testing Guide

Руководство по тестированию webhook локально.

---

## 📋 Текущее состояние

### Активные боты:
| Bot Username | Bot ID | Статус | Webhook URL |
|-------------|---------|--------|-------------|
| telega_audit_bot | 74702bd7 | running | Не установлен |
| Test14667bot | d485d6dc | creating | Не установлен |

---

## 🚀 Быстрый старт

### Вариант 1: Тестирование с webhook tester (рекомендуется)

```bash
# 1. Запустить webhook tester
python3 scripts/webhook-tester.py &
# Запустится на порту 8080

# 2. Перезапустить nginx с новой конфигурацией
docker-compose restart nginx

# 3. Проверить что webhook tester работает
curl http://localhost:8080/health
# Должно вернуть: {"status": "healthy", "service": "webhook-tester"}

# 4. Тестировать webhook отправку
curl -X POST http://localhost:8080/webhook/74702bd7 \
  -H "Content-Type: application/json" \
  -d '{
    "update_id": 123,
    "message": {
      "text": "Test message from webhook"
    }
  }'
```

### Вариант 2: Использовать реальные Telegram токены

```bash
# 1. Запустить скрипт настройки webhook
python3 scripts/setup-webhooks-local.py

# Скрипт сделает:
# - Расшифрует токены ботов из БД
# - Установит webhook на http://localhost/webhook/{bot_id}
# - Обновит webhook_url в БД
# - Проверит webhook info через Telegram API
```

### Вариант 3: Переключить ботов в webhook режим

```bash
# 1. Перезапустить боты в webhook режиме
python3 scripts/switch-to-webhook-mode.py

# Это попросит factory service перезапустить контейнеры ботов с USE_WEBHOOK=1
```

---

## 📊 Архитектура локального тестирования

```
┌────────────────────────────────────────────────────────┐
│                Telegram Bot API                      │
│                      │
│       POST /setWebhook    │
│           webhook_url=http://.../webhook/{bot_id}  │
│                      │
│                ┌─────────────────────────────────┐ │
│                │                           │
┌──────────┼──────────────────────────────┼─────────────────────────────────────────────────────┐
│          │                           │                                     │          │
│ Telegram  │  POST /sendMessage         │                                     │          │
│ Client    │                           │                                     │          │
│          │                           │                                     │          │
└──────────┼──────────────────────────────┼─────────────────────────────────────────────────────┘
│          │                           │                                     │          │
│          │                           │                                     │          │
│          │                           │                                     │          │
└──────────┴──────────────────────────────┴─────────────────────────────────────────────────────┘
│                      │
└────────────────────────────────────────────────────────┘
         │
         ▼
         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                  nginx (port 80)                           │
│                                                               │
│  Location: /webhook/{bot_id}                           │
│      ↓                                                │
│  ┌──────────────┐                                     │
│  │ webhook     │                                     │
│  │ tester      │                                     │
│  │ (port 8080) │                                     │
│  └──────────────┘                                     │
│                                                               │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Конфигурация

### Environment Variables (.env):

```bash
# Webhook Configuration
WEBHOOK_BASE_URL=http://localhost    # Локальное тестирование
WEBHOOK_PORT=8080                        # Port webhook tester
WEBHOOK_SECRET_TOKEN=my_secret_token     # Secret token (опционально)

# Existing
ENCRYPTION_KEY=0EpHdOi8hM9AOLSr0h_JO1Yo1iiME-ekHlX2va_M8U0
DATABASE_URL=postgresql://postgres:postgres@database:5432/bot_saas
FACTORY_SERVICE_URL=http://factory-service:8002
```

### Docker Compose:

nginx конфигурация автоматически включает webhook tester на порту 8080.

---

## 📝 API Endpoint'ы

### Webhook Tester:
- `GET /` - API info
- `GET /health` - Health check
- `POST /webhook/{bot_id}` - Telegram webhook endpoint
- `GET /webhooks` - Список доступных ботов

---

## 🧪 Тестовые сценарии

### Сценарий 1: Базовый webhook
```bash
curl -X POST http://localhost:8080/webhook/74702bd7 \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "text": "Hello from webhook!"
    }
  }'
```

### Сценарий 2: Telegram update
```bash
curl -X POST http://localhost:8080/webhook/74702bd7 \
  -H "Content-Type: application/json" \
  -d '{
    "update_id": 1001,
    "message": {
      "text": "Test message",
      "from": {"id": 123, "first_name": "Test"}
    }
  }'
```

### Сценарий 3: Callback query
```bash
curl -X POST http://localhost:8080/webhook/74702bd7 \
  -H "Content-Type: application/json" \
  -d '{
    "callback_query": {
      "id": "123"
    }
  }'
```

---

## 🐛 Troubleshooting

### Webhook не устанавливается:

**Проверьте:**
1. Nginx запущен: `docker ps | grep nginx`
2. Webhook tester запущен: `curl http://localhost:8080/health`
3. Конфигурация обновлена: `docker-compose restart nginx`

### Бот в polling режиме:

**Причина:** USE_WEBHOOK=0 или переменная не установлена

**Решение:**
```bash
# Переменные окружения для ботов
docker exec bot_74702bd7 env | grep USE_WEBHOOK
# Должно быть: USE_WEBHOOK=1

# Перезапустить бота
docker restart bot_74702bd7
```

### Ngrok нужен для внешнего webhook:

Если хотите использовать реальный домен вместо localhost:
1. Установите ngrok: `brew install ngrok`
2. Запустите: `ngrok http 80`
3. Обновите .env: `WEBHOOK_BASE_URL=https://...`
4. Обновите webhook: `python3 scripts/setup-webhooks-local.py`

---

## 📞 Поддержка

### Для просмотра логов webhook:
```bash
# Логи webhook tester
tail -f webhook-tester.log

# Nginx access logs
docker logs bot_saas_nginx -f | grep webhook
```

### Для проверки webhook в Telegram:
```bash
# Используйте скрипт для проверки
python3 scripts/set-bot-webhook.py \
    {BOT_TOKEN} \
    get

# Используйте @BotFather в Telegram
/Webhookinfo
```

---

**Версия:** 1.0.0
**Последнее обновление:** 2026-03-15
