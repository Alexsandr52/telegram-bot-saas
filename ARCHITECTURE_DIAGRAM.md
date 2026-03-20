# 🏗️ Схема работы системы - Telegram Bot SaaS

**Версия:** 1.0
**Последнее обновление:** 2026-03-17

---

## 📊 Общая архитектура системы

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL WORLD                              │
│                                                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │   Telegram   │  │   Web Panel  │  │   Payments   │               │
│  │   API/Bots   │  │   (Masters)  │  │   (Future)   │               │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘               │
│         │                 │                 │                          │
└─────────┼─────────────────┼─────────────────┼──────────────────────────┘
          │                 │                 │
          │                 ▼                 │
          │         ┌───────────────┐         │
          │         │     Nginx     │         │
          │         │  (Gateway)    │         │
          │         │   SSL, L7 LB  │         │
          │         └───────┬───────┘         │
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ PlatformBot   │   │   Web API     │   │  Bot Template │
│ (Main Bot)    │   │  (REST API)   │   │  (Masters')   │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        │         ┌─────────┼─────────┐       │
        │         ▼         ▼         ▼       │
        │  ┌──────────┐ ┌──────────┐ ┌──────┐ │
        │  │ Factory  │ │ Billing  │ │ Notif│ │
        │  │ Service  │ │ Service  │ │ Serv │ │
        │  └────┬─────┘ └────┬─────┘ └───┬──┘ │
        │       │           │           │    │
        │       └───────────┼───────────┘    │
        │                   │                │
        └───────────────────┼────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  PostgreSQL   │   │    Redis      │   │   Docker API  │
│   (Database)  │   │ (Cache/Queue) │   │  (Containers) │
└───────────────┘   └───────────────┘   └───────────────┘
```

---

## 🔄 Поток создания бота мастером

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Master Creates Bot Flow                            │
└─────────────────────────────────────────────────────────────────────────────┘

1. MASTER → @BotFather
   ┌──────────────────────────────┐
   │ /newbot                     │
   │ → Bot name                  │
   │ → Bot username (@my_bot)     │
   │ → Bot token (123:ABC...)    │
   └──────────────────────────────┘
                                    │
                                    ▼

2. MASTER → Platform Bot
   ┌──────────────────────────────┐
   │ /start                       │
   │ → "➕ Добавить бота"         │
   │ → Ввод token: 123:ABC...    │
   └──────────────────────────────┘
                                    │
                                    ▼

3. Platform Bot → Database
   ┌──────────────────────────────┐
   │ INSERT INTO masters         │
   │   (telegram_id, username)   │
   │                             │
   │ INSERT INTO bots             │
   │   (master_id, bot_token,    │
   │    bot_username, status)     │
   └──────────────────────────────┘
                                    │
                                    ▼

4. Platform Bot → Factory Service
   ┌──────────────────────────────┐
   │ POST /api/v1/factory/bots/  │
   │ {                           │
   │   "bot_id": "uuid",         │
   │   "bot_token": "encrypted",  │
   │   "bot_username": "@my_bot"  │
   │ }                           │
   └──────────────────────────────┘
                                    │
                                    ▼

5. Factory Service → Docker API
   ┌──────────────────────────────┐
   │ docker run -d \             │
   │   --name bot_{uuid} \       │
   │   --network bot_saas \      │
   │   -e BOT_ID={uuid} \       │
   │   -e BOT_TOKEN={token} \   │
   │   -e DATABASE_URL=... \     │
   │   bot-template:latest       │
   └──────────────────────────────┘
                                    │
                                    ▼

6. Factory Service → Database
   ┌──────────────────────────────┐
   │ UPDATE bots                 │
   │ SET container_status =      │
   │   'running',               │
   │     container_id = 'abc123' │
   │ WHERE id = {uuid}          │
   └──────────────────────────────┘
                                    │
                                    ▼

7. Factory Service → Platform Bot
   ┌──────────────────────────────┐
   │ Notification:               │
   │ "✅ Бот @my_bot создан!    │
   │  Готов к работе!"          │
   └──────────────────────────────┘
```

---

## 📅 Поток записи клиента

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Client Booking Flow                               │
└─────────────────────────────────────────────────────────────────────────────┘

1. CLIENT → Master's Bot
   ┌──────────────────────────────┐
   │ /start                       │
   │ → "Привет! Выберите услугу" │
   │   [Услуга 1] [Услуга 2]    │
   └──────────────────────────────┘
                                    │
                                    ▼

2. Bot Template → Database
   ┌──────────────────────────────┐
   │ SELECT * FROM services      │
   │ WHERE bot_id = {uuid}      │
   │   AND is_active = TRUE      │
   └──────────────────────────────┘
                                    │
                                    ▼

3. CLIENT → Selects Service
   ┌──────────────────────────────┐
   │ → "Услуга 1"               │
   │ → "Выберите дату"           │
   │   [Сегодня] [Завтра] [...]  │
   └──────────────────────────────┘
                                    │
                                    ▼

4. CLIENT → Selects Date & Time
   ┌──────────────────────────────┐
   │ → "Завтра"                 │
   │ → "Выберите время"          │
   │   [10:00] [11:00] [12:00]  │
   │ → "12:00"                  │
   └──────────────────────────────┘
                                    │
                                    ▼

5. Bot Template → Database
   ┌──────────────────────────────┐
   │ Check slot availability:    │
   │ SELECT * FROM appointments   │
   │ WHERE bot_id = {uuid}       │
   │   AND start_time = {time}   │
   │   AND status != 'cancelled' │
   │                             │
   │ Slot is available! ✅       │
   └──────────────────────────────┘
                                    │
                                    ▼

6. Bot Template → Database
   ┌──────────────────────────────┐
   │ INSERT INTO appointments     │
   │ (bot_id, client_id,         │
   │  service_id, start_time,   │
   │  status = 'pending')       │
   │                             │
   │ INSERT INTO clients         │
   │ (bot_id, telegram_id, ...) │
   └──────────────────────────────┘
                                    │
                                    ▼

7. Bot Template → Client
   ┌──────────────────────────────┐
   │ "✅ Вы записаны на          │
   │  Услуга 1 завтра в 12:00!  │
   │  Ждем вас! 😊"              │
   └──────────────────────────────┘
                                    │
                                    ▼

8. Bot Template → Notification Service
   ┌──────────────────────────────┐
   │ Schedule reminders:         │
   │ - 24h before appointment    │
   │ - 2h before appointment    │
   └──────────────────────────────┘
                                    │
                                    ▼

9. Notification Service → Redis Queue
   ┌──────────────────────────────┐
   │ RPUSH notifications:queue    │
   │ {                           │
   │   "send_at": "-24h",        │
   │   "recipient": {client_id},  │
   │   "message": "Напоминание..."│
   │ }                           │
   └──────────────────────────────┘
                                    │
                                    ▼

10. Bot Template → Master
    ┌──────────────────────────────┐
    │ "🔔 Новая запись!          │
    │  Клиент: @client           │
    │  Услуга: Услуга 1         │
    │  Время: Завтра 12:00"     │
    └──────────────────────────────┘
```

---

## 🔔 Поток уведомлений

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Notification Flow                                    │
└─────────────────────────────────────────────────────────────────────────────┘

1. CREATION (When appointment is made)
   ┌──────────────────────────────┐
   │ Bot Template               │
   │   → Schedule reminders     │
   │   → INSERT INTO             │
   │     notifications_queue     │
   │   (24h, 2h before)        │
   └──────────────────────────────┘
                                    │
                                    ▼

2. PROCESSING (Every 5 minutes)
   ┌──────────────────────────────┐
   │ Notification Service Worker │
   │                             │
   │ SELECT * FROM               │
   │ notifications_queue         │
   │ WHERE send_at <= NOW()      │
   │   AND status = 'pending'   │
   │ LIMIT 10                   │
   └──────────────────────────────┘
                                    │
                                    ▼

3. SENDING
   ┌──────────────────────────────┐
   │ FOR EACH notification:      │
   │                             │
   │ Bot.send_message(          │
   │   chat_id={client_id},      │
   │   text={message}           │
   │ )                           │
   │                             │
   │ UPDATE notifications_queue   │
   │ SET status = 'sent'         │
   │ WHERE id = {notif_id}      │
   └──────────────────────────────┘
                                    │
                                    ▼

4. RETRY (On failure)
   ┌──────────────────────────────┐
   │ IF send_message failed:     │
   │                             │
   │ UPDATE notifications_queue   │
   │ SET attempts = attempts+1   │
   │ WHERE id = {notif_id}      │
   │                             │
   │ IF attempts < max_attempts:│
   │   schedule retry (5min)     │
   │ ELSE:                       │
   │   status = 'failed'         │
   │   log error                │
   └──────────────────────────────┘
```

---

## 🌐 Webhook Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Webhook Request Flow                             │
└─────────────────────────────────────────────────────────────────────────────┘

1. CLIENT → Telegram Bot
   ┌──────────────────────────────┐
   │ Client sends:               │
   │ "/start"                    │
   └──────────────────────────────┘
                                    │
                                    ▼

2. Telegram API → Your Server
   ┌──────────────────────────────┐
   │ POST https://api.server.com/ │
   │       webhook/{bot_id}      │
   │                             │
   │ Headers:                    │
   │   X-Telegram-Bot-Api-Secret│
   │     -Token: {secret}        │
   │                             │
   │ Body:                       │
   │   {update JSON}             │
   └──────────────────────────────┘
                                    │
                                    ▼

3. Nginx (Gateway)
   ┌──────────────────────────────┐
   │ location /webhook/ {       │
   │   proxy_pass               │
   │     http://bot_webhooks;    │
   │                             │
   │   Validate secret token     │
   │   Extract bot_id from URL    │
   │   Route to container        │
   │ }                           │
   └──────────────────────────────┘
                                    │
                                    ▼

4. Bot Template Container
   ┌──────────────────────────────┐
   │ @router.post(              │
   │   "/webhook/{bot_id}"      │
   │ )                           │
   │                             │
   │ aiogram processes update     │
   │ Calls appropriate handler   │
   │ (start command)             │
   └──────────────────────────────┘
                                    │
                                    ▼

5. Bot Response
   ┌──────────────────────────────┐
   │ Handler sends reply:        │
   │ bot.send_message(          │
   │   chat_id={client_id},      │
   │   text="Привет! ..."       │
   │ )                           │
   └──────────────────────────────┘
                                    │
                                    ▼

6. Response to Telegram API
   ┌──────────────────────────────┐
   │ HTTP 200 OK                │
   │ {                          │
   │   "method": "sendMessage",  │
   │   "chat_id": {client_id},  │
   │   "text": "Привет! ..."    │
   │ }                          │
   └──────────────────────────────┘
```

---

## 💾 Database Schema

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Database Relationships                           │
└─────────────────────────────────────────────────────────────────────────────┘

┌────────────────┐       ┌────────────────┐       ┌────────────────┐
│     masters    │       │     bots       │       │   services     │
└────────┬───────┘       └────────┬───────┘       └────────┬───────┘
         │                        │                        │
         │ 1:N                    │ 1:N                    │ 1
         │                        │                        │
         ▼                        ▼                        │
┌────────────────┐       ┌────────────────┐              │
│     bots      │<──────│   services    │              │
│              │       │              │              │
└───────┬──────┘       └──────────────┘              │
        │ 1:N                                        │
        │                                            │ N:1
        │ 1:N                                        │
        ▼                                            │
┌────────────────┐                              ┌─────┴──────┐
│  schedules    │                              │ services   │
└────────────────┘                              └────────────┘

┌────────────────┐       ┌────────────────┐       ┌────────────────┐
│     bots      │       │   clients     │       │ appointments  │
└────────┬───────┘       └────────┬───────┘       └────────┬───────┘
         │ 1:N                    │ 1:N                    │
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                │ 1:N
                                │
┌────────────────┐       ┌────────────────┐
│ appointments  │       │    masters    │
└────────────────┘       └────────────────┘
         │ 1:N                    │
         │                        │ 1:N
         ▼                        ▼
┌────────────────┐       ┌────────────────┐
│notifications_ │       │ subscriptions │
│    queue      │       └────────────────┘
└────────────────┘
```

---

## 🔐 Security Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Security Layers                                 │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ Layer 1: Network Security                                                 │
│   • Firewall (UFW)                                                      │
│   • SSL/TLS (Let's Encrypt)                                             │
│   • Rate Limiting (Nginx)                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Layer 2: API Gateway                                                     │
│   • Request validation                                                   │
│   • Secret token validation (webhooks)                                    │
│   • CORS checks                                                         │
│   • Request sanitization                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Layer 3: Application Security                                            │
│   • JWT authentication                                                  │
│   • Bot token encryption (Fernet)                                        │
│   • Input validation (Pydantic)                                         │
│   • SQL injection prevention (asyncpg)                                   │
│   • XSS prevention                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Layer 4: Database Security                                              │
│   • Row-level security (RLS)                                            │
│   • Foreign key constraints                                             │
│   • Encrypted sensitive data                                             │
│   • Connection pooling                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Deployment Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Deployment Process                                 │
└─────────────────────────────────────────────────────────────────────────────┘

1. LOCAL DEVELOPMENT
   ┌──────────────────────────────┐
   │ Code changes               │
   │ Git commit                 │
   └──────────────────────────────┘
                                    │
                                    ▼

2. CI/CD (Future)
   ┌──────────────────────────────┐
   │ GitHub Actions             │
   │ → Run tests               │
   │ → Build Docker images      │
   │ → Push to registry        │
   └──────────────────────────────┘
                                    │
                                    ▼

3. PRODUCTION SERVER
   ┌──────────────────────────────┐
   │ SSH to server              │
   │ git pull                  │
   │ docker-compose pull       │
   │ docker-compose up -d      │
   │ docker-compose restart     │
   └──────────────────────────────┘
                                    │
                                    ▼

4. MIGRATIONS
   ┌──────────────────────────────┐
   │ docker-compose exec        │
   │   database psql -U ...    │
   │   -f migrations/...       │
   └──────────────────────────────┘
                                    │
                                    ▼

5. WEBHOOK UPDATE
   ┌──────────────────────────────┐
   │ python3 scripts/          │
   │   update-all-webhooks.py   │
   └──────────────────────────────┘
                                    │
                                    ▼

6. VERIFICATION
   ┌──────────────────────────────┐
   │ Test critical flows        │
   │ Check logs                │
   │ Monitor metrics           │
   └──────────────────────────────┘
```

---

## 📊 Service Communication

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Service Communication Matrix                          │
└─────────────────────────────────────────────────────────────────────────────┘

               │ Platform │ Factory │   Bot   │  Web   │ Notif  │ Billing
               │   Bot    │ Service │Template │  API   │ Service│ Service
───────────────┼──────────┼─────────┼─────────┼────────┼────────┼─────────
Platform Bot   │    -     │   HTTP  │   N/A   │   -    │   -    │    N/A
Factory Svc    │   HTTP    │    -    │  Docker │   -    │   -    │    N/A
Bot Template   │  N/A     │  N/A    │    -    │   -    │  HTTP   │    N/A
Web API        │    -     │   HTTP   │   N/A   │   -    │   -    │    N/A
Notif Service  │    -     │    -    │  HTTP   │   -    │    -    │    N/A
Billing Svc    │  N/A     │    -    │   N/A   │  HTTP   │   -    │    -
───────────────┼──────────┼─────────┼─────────┼────────┼────────┼─────────
Database       │  asyncpg │ asyncpg │ asyncpg │asyncpg │ asyncpg │ asyncpg
Redis          │  aioredis│    -    │    -    │    -   │ aioredis│    -

Protocol Legend:
  HTTP  = REST API (FastAPI)
  Docker = Docker API (python-docker)
  asyncpg = PostgreSQL connection (async)
  aioredis = Redis connection (async)
  N/A = Not applicable / Not needed
```

---

## 🔄 Data Flow Examples

### Example 1: Adding a Service
```
Master → Platform Bot → Web API → Database → Bot Template (cache reload)
```

### Example 2: Booking an Appointment
```
Client → Bot Template → Database → Notification Service → Redis Queue
         ↓                                              ↓
    Confirmation                                   Processing
         ↓                                              ↓
    Master (alert)                               Telegram API
```

### Example 3: Sending Reminder
```
Notification Service Worker → Redis Queue → Bot Template → Telegram API → Client
```

---

## 📝 Notes

- **Isolation:** Each master's bot runs in a separate Docker container
- **Shared Resources:** All containers share the same PostgreSQL and Redis
- **Scalability:** Horizontal scaling possible for API services
- **High Availability:** Can add load balancers and database replicas
- **Monitoring:** Logging service collects logs from all containers

---

**Версия:** 1.0
**Последнее обновление:** 2026-03-17
**Статус документа:** 🟢 Актуальный
