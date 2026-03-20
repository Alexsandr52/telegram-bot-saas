# 🖼️ Визуализация системы - Telegram Bot SaaS

**Версия:** 1.0
**Дата:** 2026-03-17

---

## 🎯 Общая схема (High-Level)

```
                    ┌──────────────────────────────────────────────┐
                    │            EXTERNAL WORLD                   │
                    │                                            │
                    │  ┌──────────┐   ┌──────────┐   ┌─────┐  │
                    │  │ Telegram │   │Web Panel │   │Payments│  │
                    │  │  (Users) │   │(Masters) │   │(Future)│  │
                    │  └────┬─────┘   └────┬─────┘   └───┬─┘  │
                    └───────┼─────────────┼─────────────┼──────┘
                            │             │             │
                            └─────────────┼─────────────┘
                                          │
                        ┌─────────────────┼─────────────────┐
                        │                 │                 │
                        ▼                 ▼                 ▼
              ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
              │   Nginx     │   │Platform Bot │   │  Bot Tmpl  │
              │  (Gateway)  │   │  (Masters)  │   │  (Clients)  │
              └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
                     │                 │                 │
                     └─────────────────┼─────────────────┘
                                     │
          ┌────────────────────────────┼────────────────────────────┐
          │                        │                        │
          ▼                        ▼                        ▼
┌─────────────┐          ┌─────────────┐          ┌─────────────┐
│   Factory   │          │   Web API   │          │ Notification│
│  Service    │          │   (REST)    │          │  Service    │
└──────┬──────┘          └──────┬──────┘          └──────┬──────┘
       │                       │                       │
       └───────────────────────┼───────────────────────┘
                               │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│ PostgreSQL   │       │    Redis    │       │  Docker API  │
│  (Database) │       │ (Cache/Queue)│       │(Containers) │
└─────────────┘       └─────────────┘       └─────────────┘
```

---

## 🔄 Поток создания бота (Step-by-Step)

```
STEP 1: MASTERS REGISTERS
┌───────────────┐
│  Master       │
│  (@user123)   │
└───────┬───────┘
        │
        │ 1. /start in Platform Bot
        ▼
┌───────────────────────────────────────┐
│  Platform Bot                       │
│  → Creates master record in DB       │
│  → Sends welcome message            │
│  → Shows menu                       │
└───────────────────────────────────────┘

STEP 2: MASTER CREATES BOT
┌───────────────┐
│  Master       │
│  (@user123)   │
└───────┬───────┘
        │
        │ 2. /newbot in @BotFather
        ▼
┌───────────────────────────────────────┐
│  @BotFather                        │
│  → Bot name: My Salon               │
│  → Username: @mysalon_bot          │
│  → Token: 123456:ABC...           │
└───────────────────────────────────────┘
        │
        │ 3. Copies token
        ▼
┌───────────────┐
│  Master       │
│  (@user123)   │
└───────┬───────┘
        │
        │ 4. Sends token to Platform Bot
        ▼
┌───────────────────────────────────────┐
│  Platform Bot                       │
│  → Encrypts token                   │
│  → Saves to DB                     │
│  → Calls Factory Service            │
└───────────────────────────────────────┘
        │
        │ 5. POST /api/v1/factory/bots/
        ▼
┌───────────────────────────────────────┐
│  Factory Service                    │
│  → Validates request                │
│  → Calls Docker API                │
└───────────────────────────────────────┘
        │
        │ 6. docker run -d bot-template
        ▼
┌───────────────────────────────────────┐
│  Docker API                         │
│  → Creates container                │
│  → Returns container ID             │
└───────────────────────────────────────┘
        │
        │ 7. Container started
        ▼
┌───────────────────────────────────────┐
│  Bot Template Container              │
│  ID: bot_{uuid}                    │
│  → Connects to DB                  │
│  → Loads config                     │
│  → Starts webhook/polling           │
│  → Ready for clients!               │
└───────────────────────────────────────┘
        │
        │ 8. Updates bot status
        ▼
┌───────────────────────────────────────┐
│  Database                           │
│  UPDATE bots SET status = 'running' │
└───────────────────────────────────────┘
        │
        │ 9. Notification
        ▼
┌───────────────────────────────────────┐
│  Master (@user123)                  │
│  "✅ Bot @mysalon_bot created!"      │
└───────────────────────────────────────┘
```

---

## 📅 Поток записи клиента (Step-by-Step)

```
STEP 1: CLIENT STARTS BOT
┌───────────────┐
│  Client       │
│  (@client456) │
└───────┬───────┘
        │
        │ 1. /start @mysalon_bot
        ▼
┌───────────────────────────────────────┐
│  Telegram API                       │
│  → Forwards update to webhook        │
└───────────────────────────────────────┘
        │
        │ 2. POST /webhook/{bot_id}
        ▼
┌───────────────────────────────────────┐
│  Nginx → Bot Template Container    │
│  → Processes /start command         │
│  → Shows services menu              │
└───────────────────────────────────────┘
        │
        │ 3. Returns to client
        ▼
┌───────────────────────────────────────┐
│  Client (@client456)                │
│  "Welcome! Choose service:"          │
│  [Haircut] [Nails] [Makeup]        │
└───────────────────────────────────────┘

STEP 2: SELECTS SERVICE
┌───────────────┐
│  Client       │
│  (@client456) │
└───────┬───────┘
        │
        │ 4. Clicks [Haircut]
        ▼
┌───────────────────────────────────────┐
│  Bot Template                       │
│  → SELECT * FROM services           │
│    WHERE bot_id = {uuid}             │
│  → Shows date picker                │
└───────────────────────────────────────┘

STEP 3: SELECTS DATE & TIME
┌───────────────┐
│  Client       │
│  (@client456) │
└───────┬───────┘
        │
        │ 5. Clicks [Tomorrow] → [14:00]
        ▼
┌───────────────────────────────────────┐
│  Bot Template                       │
│  → Check availability               │
│  → INSERT INTO appointments          │
│  → Create client record            │
│  → Schedule reminders              │
└───────────────────────────────────────┘
        │
        │ 6. Updates DB
        ▼
┌───────────────────────────────────────┐
│  Database                           │
│  INSERT INTO appointments            │
│  INSERT INTO notifications_queue     │
│    (24h reminder, 2h reminder)    │
└───────────────────────────────────────┘
        │
        │ 7. Confirms to client
        ▼
┌───────────────────────────────────────┐
│  Client (@client456)                │
│  "✅ Booked! Haircut tomorrow      │
│   at 14:00. See you!"              │
└───────────────────────────────────────┘
        │
        │ 8. Notifies master
        ▼
┌───────────────────────────────────────┐
│  Master (@user123)                  │
│  "🔔 New booking!                  │
│   Client: @client456                │
│   Service: Haircut                  │
│   Time: Tomorrow 14:00"             │
└───────────────────────────────────────┘

STEP 4: REMINDERS (24h + 2h)
┌───────────────────────────────────────┐
│  Notification Service Worker         │
│  (Runs every 5 min)                │
│  → SELECT * FROM notifications       │
│    WHERE send_at <= NOW()           │
│  → For each:                       │
│    Bot.send_message(...)            │
│  → UPDATE status = 'sent'          │
└───────────────────────────────────────┘
        │
        │ 9. Sends reminders
        ▼
┌───────────────────────────────────────┐
│  Client (@client456)                │
│  "⏰ Reminder: Haircut tomorrow    │
│   at 14:00!"                       │
└───────────────────────────────────────┘
```

---

## 🔗 Сервисы и их зависимости

```
                    ┌─────────────────────────────┐
                    │         Dependencies         │
                    └─────────────────────────────┘

┌─────────────────┐         ┌─────────────────┐
│  Platform Bot  │────────▶│  PostgreSQL    │
│  (Port 8001)   │         │  (Port 5432)   │
└─────────────────┘         └─────────────────┘
        │                          ▲
        │                          │
        ▼                          │
┌─────────────────┐         ┌─────────────────┐
│  Factory Svc   │────────▶│  PostgreSQL    │
│  (Port 8002)   │         └─────────────────┘
└─────────────────┘         ┌─────────────────┐
        │                  │    Redis       │
        │                  │  (Port 6379)   │
        ▼                  └─────────────────┘
┌─────────────────┐
│  Bot Template  │────────▶┌─────────────────┐
│  (Per Master)  │         │  PostgreSQL    │
└─────────────────┘         └─────────────────┘
        │                          ▲
        │                          │
        ▼                          │
┌─────────────────┐         ┌─────────────────┐
│  Web API       │────────▶│  PostgreSQL    │
│  (Port 8000)   │         └─────────────────┘
└─────────────────┘

┌─────────────────┐         ┌─────────────────┐
│ Notification   │────────▶│    Redis       │
│  Service       │         └─────────────────┘
│  (Port 8003)   │         ┌─────────────────┐
└─────────────────┘────────▶│  PostgreSQL    │
                           └─────────────────┘

┌─────────────────┐         ┌─────────────────┐
│  Web Panel     │────────▶│  Web API      │
│  (Port 3000)   │         │  (Port 8000)   │
└─────────────────┘         └─────────────────┘
```

---

## 📊 Таблица сервисов

| Сервис | Порт | Назначение | Зависимости |
|--------|------|------------|-------------|
| **Nginx** | 80/443 | API Gateway, SSL | Все сервисы |
| **Platform Bot** | - | Главный бот для мастеров | PostgreSQL |
| **Factory Service** | 8002 | Управление контейнерами | PostgreSQL, Docker API |
| **Bot Template** | - | Бот для клиентов (N штук) | PostgreSQL |
| **Web API** | 8000 | REST API для веб-панели | PostgreSQL |
| **Web Panel** | 3000 → 80 | Веб-интерфейс мастеров | Web API |
| **Notification Service** | - | Уведомления и напоминания | PostgreSQL, Redis |
| **Logging Service** | 8001 | Централизованное логирование | PostgreSQL |
| **PostgreSQL** | 5432 | База данных | - |
| **Redis** | 6379 | Кеш и очереди | - |
| **pgAdmin** | 5050 | UI для БД | PostgreSQL |
| **Redis Commander** | 8082 | UI для Redis | Redis |

---

## 🔐 Безопасность по слоям

```
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 1: NETWORK                                          │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ • Firewall (UFW)                                    │   │
│ │ • SSL/TLS (Let's Encrypt)                           │   │
│ │ • Rate Limiting (Nginx: 100 req/min)                │   │
│ └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 2: API GATEWAY                                      │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ • Request validation                                 │   │
│ │ • Secret token validation (webhooks)                 │   │
│ │ • CORS checks                                       │   │
│ │ • Request sanitization                              │   │
│ └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 3: APPLICATION                                       │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ • JWT authentication                                  │   │
│ │ • Bot token encryption (Fernet)                      │   │
│ │ • Input validation (Pydantic)                        │   │
│ │ • SQL injection prevention (asyncpg)                  │   │
│ │ • XSS prevention                                     │   │
│ └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 4: DATABASE                                         │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ • Row-level security (RLS)                           │   │
│ │ • Foreign key constraints                            │   │
│ │ • Encrypted sensitive data                           │   │
│ │ • Connection pooling                                 │   │
│ └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📈 Масштабирование

```
CURRENT SCALE (MVP):
┌─────────────────────────────────────────────────────────────────┐
│ • 1 PostgreSQL instance                                       │
│ • 1 Redis instance                                           │
│ • 1 Platform Bot                                            │
│ • 1 Factory Service                                         │
│ • 1 Web API                                                 │
│ • N Bot Template containers (N = number of masters)           │
│ • 1 Notification Service                                     │
│                                                             │
│ Capacity: Up to 50 masters, 100 bots, 1000 appointments/mo  │
└─────────────────────────────────────────────────────────────────┘

FUTURE SCALE (Production):
┌─────────────────────────────────────────────────────────────────┐
│ • PostgreSQL Primary + Replica (HA)                            │
│ • Redis Cluster                                             │
│ • Nginx Load Balancer                                        │
│ • Multiple Platform Bot instances                            │
│ • Multiple Factory Service instances                         │
│ • Multiple Web API instances (auto-scaled)                   │
│ • Bot containers on separate servers                          │
│ • Prometheus + Grafana monitoring                            │
│ • Automatic backups                                         │
│                                                             │
│ Capacity: 1000+ masters, 5000+ bots                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Webhook vs Polling

```
POLLING MODE (Development):
┌─────────────────────────────────────────────────────────────────┐
│ Bot Template                                              │
│    │                                                        │
│    ├─→ Poll Telegram API every 10 seconds                    │
│    │   GET https://api.telegram.org/bot{token}/getUpdates    │
│    │                                                        │
│    └─→ Process updates                                     │
│        • /start                                            │
│        • Button clicks                                      │
│        • Text messages                                     │
│                                                             │
│ Pros: Easy to setup, no public domain needed                 │
│ Cons: Delayed responses, higher API usage                   │
└─────────────────────────────────────────────────────────────────┘

WEBHOOK MODE (Production):
┌─────────────────────────────────────────────────────────────────┐
│ Client                                                    │
│    │                                                        │
│    ├─→ Sends message to Telegram                            │
│    │                                                        │
│    ▼                                                        │
│ Telegram API                                               │
│    │                                                        │
│    ├─→ POST https://yourdomain.com/webhook/{bot_id}         │
│    │   (Instant!)                                           │
│    │                                                        │
│    ▼                                                        │
│ Nginx → Bot Template Container                            │
│    │                                                        │
│    └─→ Process update immediately                           │
│                                                             │
│ Pros: Instant responses, lower API usage                    │
│ Cons: Requires public domain + SSL                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📝 Быстрый справочник

### Запуск сервиса
```bash
docker-compose up -d                    # Запустить все
docker-compose up -d platform-bot        # Запустить один
docker-compose restart platform-bot        # Перезапустить
docker-compose logs -f platform-bot        # Логи
```

### Проверка webhook
```bash
python3 scripts/set-bot-webhook.py {TOKEN} get      # Статус
python3 scripts/set-bot-webhook.py {TOKEN} delete   # Удалить
```

### Подключение к БД
```bash
docker-compose exec database psql -U postgres -d bot_saas
```

### Просмотр контейнеров ботов
```bash
docker ps --filter "label=service=telegram-bot"
```

---

**Версия:** 1.0
**Дата:** 2026-03-17
**Статус:** 🟢 Актуальный
