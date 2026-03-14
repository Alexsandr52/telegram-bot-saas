# 🚀  Проектная Документация

> **Статус:** 🟡 В разработке  
> **Версия:** 0.1.0  
> **Последнее обновление:** {{date}}  
> **Теги:** #saas #telegram-bot #python #docker #postgresql

---

## 📋 Содержание

1. [[#Обзор проекта]]
2. [[#Архитектура системы]]
3. [[#База данных]]
4. [[#Структура проекта]]
5. [[#Сервисы и их взаимодействие]]
6. [[#Webhook-поддержка]] — NEW!
7. [[#План реализации]]
8. [[#Развёртывание]]
9. [[#Безопасность]]
10. [[#Чек-листы]]

---

## 📌 Обзор проекта

### Суть идеи
SaaS-платформа для мастеров услуг (парикмахеры, ногтевики, бровисты и т.д.), позволяющая создавать персональных Telegram-ботов для приёма записей от клиентов.

### Проблема
| Проблема | Решение |
|----------|---------|
| Запись в блокноте/заметках | Автоматизация через бота 24/7 |
| Клиенты пишут в разное время | Бот отвечает мгновенно |
| YCLIENTS/Dikidi — дорогие и сложные | Простой интерфейс в Telegram |
| Нет решения для микробизнеса в СНГ | Специализированная платформа |

### Целевая аудитория
- Самозанятые мастера услуг (25-45 лет)
- РФ и СНГ, активные пользователи Telegram
- Технически не подкованы — нужно «нажал и работает»
- Готовы платить 300-1000 ₽/мес

### Монетизация
| Тариф | Цена | Лимиты | Функции |
|-------|------|--------|---------|
| **Free** | 0 ₽ | 1 бот, 50 записей/мес | Базовая запись |
| **Pro** | 490 ₽/мес | 1 бот, безлимит | Напоминания, статистика |
| **Business** | 1990 ₽/мес | До 5 ботов | Команда, API-доступ |

---

## 🏗️ Архитектура системы

### Принцип
**1 бот мастера = 1 изолированный Docker-контейнер**

```
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway (nginx)                     │
│                    SSL, Rate Limiting, Routing               │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ PlatformBot   │   │ Factory Svc   │   │ Billing Svc   │
│ (онбординг)   │   │ (контейнеры)  │   │ (платежи)     │
└───────────────┘   └───────────────┘   └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │     + Redis     │
                    └─────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  Bot #1       │   │  Bot #2       │   │  Bot #N       │
│  (container)  │   │  (container)  │   │  (container)  │
└───────────────┘   └───────────────┘   └───────────────┘
```

### Микросервисы

| Сервис | Задача | Стек | Порт |
|--------|--------|------|------|
| **PlatformBot** | Главный бот для онбординга мастеров | Python + aiogram 3.x | 8001 |
| **Factory Service** | Создание/управление контейнерами ботов | Python + Docker SDK | 8002 |
| **Bot Template** | Базовый образ для клонирования ботов | Python + aiogram 3.x | - |
| **Notification Service** | Очередь и отправка напоминаний | Python + Celery + Redis | 8003 |
| **Billing Service** | Тарифы, подписки, платежи | Python + FastAPI + YooKassa | 8004 |
| **Monitoring Service** | Метрики, логи, дашборды | Prometheus + Grafana | 9090/3000 |
| **API Gateway** | Единая точка входа, SSL | nginx + Let's Encrypt | 80/443 |

### Инфраструктура

| Компонент | Технология | Версия |
|-----------|------------|--------|
| Язык | Python | 3.11+ |
| Боты | aiogram | 3.x |
| API | FastAPI | 0.100+ |
| БД | PostgreSQL | 15+ |
| Кеш/Очереди | Redis | 7+ |
| Контейнеры | Docker + Docker Compose | 24+ |
| Хостинг | Timeweb / Selectel / Yandex Cloud | - |
| ОС | Ubuntu | 22.04 LTS |

---

## 🗄️ База данных

### Схема отношений

```mermaid
erDiagram
    masters ||--o{ bots : owns
    masters ||--o{ subscriptions : has
    masters ||--o{ payments : makes
    bots ||--o{ services : configures
    bots ||--o{ schedules : configures
    bots ||--o{ clients : serves
    bots ||--o{ appointments : manages
    bots ||--o{ notifications_queue : uses
    bots ||--o{ analytics_events : generates
    subscriptions ||--o{ payments : billed
```

### Таблицы

#### masters
| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID | Первичный ключ |
| telegram_id | BIGINT | ID в Telegram (уникальный) |
| username | VARCHAR(255) | Никнейм |
| phone | VARCHAR(20) | Телефон |
| full_name | VARCHAR(255) | ФИО |
| is_active | BOOLEAN | Статус аккаунта |
| created_at | TIMESTAMPTZ | Дата создания |
| updated_at | TIMESTAMPTZ | Дата обновления |

#### bots
| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID | Первичный ключ |
| master_id | UUID | Ссылка на мастера (FK) |
| bot_token | VARCHAR(255) | Токен бота (уникальный, шифровать!) |
| bot_username | VARCHAR(255) | Юзернейм бота |
| container_status | VARCHAR(50) | Статус контейнера |
| container_id | VARCHAR(255) | ID Docker контейнера |
| is_active | BOOLEAN | Статус бота |
| created_at | TIMESTAMPTZ | Дата создания |
| updated_at | TIMESTAMPTZ | Дата обновления |

#### services
| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID | Первичный ключ |
| bot_id | UUID | Ссылка на бота (FK) |
| name | VARCHAR(255) | Название услуги |
| description | TEXT | Описание |
| price | DECIMAL(10,2) | Цена в рублях |
| duration_minutes | INTEGER | Длительность в минутах |
| settings | JSONB | Гибкие настройки (фото, предоплата и т.д.) |
| is_active | BOOLEAN | Статус услуги |
| sort_order | INTEGER | Порядок отображения |
| created_at | TIMESTAMPTZ | Дата создания |

#### appointments
| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID | Первичный ключ |
| bot_id | UUID | Ссылка на бота (FK) |
| client_id | UUID | Ссылка на клиента (FK) |
| service_id | UUID | Ссылка на услугу (FK) |
| start_time | TIMESTAMPTZ | Начало записи |
| end_time | TIMESTAMPTZ | Конец записи |
| status | VARCHAR(50) | pending/confirmed/completed/cancelled |
| comment | TEXT | Комментарий клиента |
| created_at | TIMESTAMPTZ | Дата создания |
| updated_at | TIMESTAMPTZ | Дата обновления |

> **Важно:** Таблица `analytics_events` — партиционированная по дате (месяц).

### Индексы (критически важные)

```sql
-- Мастера
CREATE INDEX idx_masters_telegram_id ON masters(telegram_id);

-- Боты
CREATE INDEX idx_bots_master_id ON bots(master_id);
CREATE INDEX idx_bots_token ON bots(bot_token);

-- Услуги
CREATE INDEX idx_services_bot_id ON services(bot_id);

-- Записи (самый важный индекс для календаря)
CREATE INDEX idx_appointments_bot_time ON appointments(bot_id, start_time);

-- Уведомления
CREATE INDEX idx_notifications_send_at ON notifications_queue(send_at) 
    WHERE status = 'pending';
```

---

## 📁 Структура проекта

```
telegram-bot-saas/
├── 📄 docker-compose.yml              # Оркестрация контейнеров
├── 📄 docker-compose.prod.yml         # Продакшен конфигурация
├── 📄 .env.example                    # Шаблон переменных окружения
├── 📄 README.md                       # Документация
├── 📄 WEBHOOK_SETUP.md               # Webhook настройка (ngrok + prod)
├── 📂 scripts/                       # Утилиты для webhook
│   ├── 📄 setup-ngrok.sh             # Автонастройка ngrok
│   ├── 📄 set-bot-webhook.py         # Управление webhook бота
│   └── 📄 update-all-webhooks.py      # Обновление webhook всех ботов
│
├── 📂 platform-bot/                   # Главный бот для мастеров
│   ├── 📄 Dockerfile
│   ├── 📄 requirements.txt
│   ├── 📂 src/
│   │   ├── 📄 main.py                 # Точка входа
│   │   ├── 📂 handlers/               # Обработчики сообщений
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 start.py            # /start
│   │   │   ├── 📄 connect_bot.py      # Подключение бота
│   │   │   ├── 📄 services.py         # Управление услугами
│   │   │   └── 📄 appointments.py     # Просмотр записей
│   │   ├── 📂 keyboards/              # Inline клавиатуры
│   │   ├── 📂 middlewares/            # Промежуточное ПО
│   │   └── 📂 utils/                  # Утилиты
│   └── 📂 tests/
│
├── 📂 factory-service/                # Управление контейнерами
│   ├── 📄 Dockerfile
│   ├── 📄 requirements.txt
│   ├── 📂 src/
│   │   ├── 📄 main.py
│   │   ├── 📂 api/                    # FastAPI роуты
│   │   ├── 📂 docker/                 # Docker SDK обёртки
│   │   └── 📂 models/                 # Pydantic модели
│   └── 📂 tests/
│
├── 📂 bot-template/                   # Шаблон бота мастера
│   ├── 📄 Dockerfile
│   ├── 📄 requirements.txt
│   ├── 📂 src/
│   │   ├── 📄 main.py                 # Точка входа бота
│   │   ├── 📂 handlers/
│   │   │   ├── 📄 client_menu.py      # Меню клиента
│   │   │   ├── 📄 services.py         # Выбор услуги
│   │   │   ├── 📄 booking.py          # Запись на услугу
│   │   │   └── 📄 profile.py          # Профиль клиента
│   │   ├── 📂 keyboards/
│   │   ├── 📂 services/               # Бизнес-логика
│   │   │   ├── 📄 scheduler.py        # Генерация слотов
│   │   │   └── 📄 calendar.py         # Работа с датами
│   │   └── 📂 utils/
│   │       ├── 📄 config.py           # Загрузка конфига из БД
│   │       └── 📄 db.py               # Подключение к БД
│   └── 📂 tests/
│
├── 📂 notification-service/           # Очередь уведомлений
│   ├── 📄 Dockerfile
│   ├── 📄 requirements.txt
│   ├── 📂 src/
│   │   ├── 📄 worker.py               # Celery воркер
│   │   └── 📂 tasks/
│   │       ├── 📄 reminders.py        # Напоминания клиентам
│   │       └── 📄 alerts.py           # Алерты мастерам
│   └── 📂 tests/
│
├── 📂 billing-service/                # Платежи и подписки
│   ├── 📄 Dockerfile
│   ├── 📄 requirements.txt
│   ├── 📂 src/
│   │   ├── 📄 main.py
│   │   ├── 📂 api/
│   │   ├── 📂 providers/              # ЮKassa, CloudPayments
│   │   └── 📂 models/
│   └── 📂 tests/
│
├── 📂 database/                       # Миграции БД
│   ├── 📄 schema.sql                  # Полная схема (см. выше)
│   ├── 📂 migrations/                 # Alembic миграции
│   │   ├── 📄 env.py
│   │   ├── 📄 script.py.mako
│   │   └── 📂 versions/
│   └── 📄 alembic.ini
│
├── 📂 monitoring/                     # Мониторинг
│   ├── 📄 prometheus.yml
│   ├── 📂 grafana/
│   │   └── 📂 dashboards/
│   └── 📂 alerts/
│
└── 📂 nginx/                          # Шлюз
    ├── 📄 nginx.conf                  # Базовая конфигурация
    ├── 📄 nginx-webhook.conf          # Конфигурация с webhook
    └── 📂 ssl/                       # SSL сертификаты
```

---

## 🔄 Сервисы и их взаимодействие

### PlatformBot → Factory Service
```python
# Когда мастер подключает бота
POST /api/v1/factory/bots/
{
    "master_id": "uuid",
    "bot_token": "encrypted_token",
    "bot_username": "my_master_bot"
}

# Ответ
{
    "bot_id": "uuid",
    "container_id": "abc123",
    "status": "running",
    "webhook_url": "https://api.platform.com/webhook/abc123"
}
```

### Bot Template → Database
```python
# Каждый бот-контейнер подключается к общей БД
# Но фильтрует все запросы по bot_id

async def get_services(bot_id: UUID):
    query = "SELECT * FROM services WHERE bot_id = $1 AND is_active = TRUE"
    return await db.fetch_all(query, bot_id)
```

### Notification Service → Redis Queue
```python
# Добавление задачи в очередь
await redis.lpush('notifications:queue', json.dumps({
    'bot_id': 'uuid',
    'recipient_id': 123456789,
    'message': 'Напоминание о записи завтра в 15:00',
    'send_at': '2024-01-15T14:00:00Z'
}))

# Воркер забирает и отправляет через Telegram API
```

### API Контракты

| Эндпоинт | Метод | Описание |
|----------|-------|----------|
| `/api/v1/factory/bots/` | POST | Создать контейнер бота |
| `/api/v1/factory/bots/{id}/` | DELETE | Удалить бота |
| `/api/v1/factory/bots/{id}/restart/` | POST | Перезапустить бота |
| `/api/v1/billing/subscribe/` | POST | Оформить подписку |
| `/api/v1/billing/webhook/` | POST | Вебхук от платёжной системы |
| `/api/v1/notifications/schedule/` | POST | Запланировать уведомление |

---

## 🔄 Webhook-поддержка

### Обзор
Система поддерживает два режима работы ботов:
- **Webhook** - для продакшена (мгновенное получение сообщений)
- **Long-polling** - для локальной разработки (опрос Telegram API)

### Форматы URL

#### Локальная разработка (ngrok)
```
https://{random_subdomain}.ngrok.io/webhook/{bot_id}
```
Пример: `https://abc123xyz.ngrok.io/webhook/74702bd7-8a8c-4b9e-94d6-713059abaf6e`

#### Продакшен (реальный домен)
```
https://{your_domain}/webhook/{bot_id}
```
Пример: `https://api.yourdomain.com/webhook/74702bd7-8a8c-4b9e-94d6-713059abaf6e`

### Скрипты для управления

| Скрипт | Описание |
|---------|----------|
| `scripts/setup-ngrok.sh` | Автоматическая настройка ngrok туннеля |
| `scripts/set-bot-webhook.py` | Установка/удаление webhook для одного бота |
| `scripts/update-all-webhooks.py` | Обновление webhook для всех ботов сразу |

### Быстрый старт с ngrok

```bash
# 1. Настроить переменные окружения
echo "NGROK_ENABLED=true" >> .env

# 2. Запустить ngrok
./scripts/setup-ngrok.sh
# Скрипт покажет: https://abc123.ngrok.io

# 3. Обновить webhook для всех ботов
export NGROK_WEBHOOK_URL=https://abc123.ngrok.io
python3 scripts/update-all-webhooks.py

# 4. Проверить статус webhook
python3 scripts/set-bot-webhook.py {BOT_TOKEN} get
```

### Переход на продакшен

```bash
# 1. Настроить DNS
# A запись: yourdomain.com → YOUR_SERVER_IP

# 2. Получить SSL сертификат
sudo certbot certonly --standalone -d api.yourdomain.com

# 3. Скопировать сертификаты
sudo cp /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/api.yourdomain.com/privkey.pem nginx/ssl/

# 4. Обновить .env
NGROK_ENABLED=false
SERVER_DOMAIN=api.yourdomain.com
WEBHOOK_BASE_URL=https://api.yourdomain.com

# 5. Обновить webhook для всех ботов
python3 scripts/update-all-webhooks.py

# 6. Перезапустить nginx
docker-compose restart nginx
```

### Nginx конфигурация

Файл: `nginx/nginx-webhook.conf`

```nginx
location /webhook/ {
    # Проксирование webhook запросов к ботам
    proxy_pass http://bot_webhooks;
    proxy_set_header X-Telegram-Bot-Id $bot_id;

    # Увеличенный таймаут для Telegram API
    proxy_read_timeout 120s;
}
```

### Безопасность webhook

#### Секретный токен
```bash
# Установка webhook с секретным токеном
python3 scripts/set-bot-webhook.py \
    {BOT_TOKEN} \
    set \
    --webhook-url {WEBHOOK_URL} \
    --secret-token "random_secret_string"
```

#### Валидация в боте
```python
# Bot template main.py
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN")

if WEBHOOK_SECRET_TOKEN:
    # aiogram автоматически валидирует секретный токен
    ...
```

### Мониторинг webhook

```bash
# Логи nginx (входящие webhook запросы)
docker logs bot_saas_nginx | grep "POST /webhook/"

# Логи бота (обработка webhook)
docker logs bot_74702bd7 -f

# Статус webhook через Telegram API
curl https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo
```

### Troubleshooting

| Проблема | Решение |
|----------|----------|
| Webhook не работает | Проверьте что ngrok запущен и URL доступен |
| 404 на webhook | Убедитесь что nginx использует `nginx-webhook.conf` |
| 500 на webhook | Проверьте логи бота, может быть проблема с БД |
| Ngrok URL меняется | Обновите webhook или используйте платный ngrok план |
| SSL ошибка | Проверьте что сертификаты корректные и не просрочены |

**Подробнее:** См. `WEBHOOK_SETUP.md` для полной документации.

---

## 📅 План реализации

### Этап 1: Прототип (2 недели)
- [ ] Настроить Docker Compose локально
- [ ] Создать БД и применить миграции
- [ ] Реализовать PlatformBot (регистрация + подключение бота)
- [ ] Реализовать Factory Service (создание контейнера)
- [ ] Реализовать Bot Template (базовая запись)
- [ ] Тест на одном мастере

### Этап 2: MVP (6 недель)
- [ ] Добавить управление услугами в PlatformBot
- [ ] Добавить управление графиком работы
- [ ] Реализовать просмотр записей для мастера
- [ ] Добавить отмену/перенос записи
- [ ] Настроить вебхуки для ботов
- [ ] Тест на 5-10 пилотных мастерах

### Этап 3: Бета (12 недель)
- [ ] Интеграция с ЮKassa
- [ ] Система подписок и тарифов
- [ ] Напоминания клиентам (24ч + 2ч до визита)
- [ ] Статистика для мастера
- [ ] База клиентов с историей
- [ ] Публичный доступ

### Этап 4: Релиз (16 недель)
- [ ] Лендинг с документацией
- [ ] Настройка продакшен-сервера
- [ ] Мониторинг и алерты
- [ ] Резервное копирование
- [ ] Реклама и привлечение пользователей

---

## 🚀 Развёртывание

### Локальная разработка

```bash
# 1. Клонировать репозиторий
git clone https://github.com/yourusername/telegram-bot-saas.git
cd telegram-bot-saas

# 2. Создать .env файл
cp .env.example .env
# Отредактировать переменные (токены, пароли)

# 3. Запустить всё через Docker Compose
docker-compose up -d

# 4. Применить миграции БД
docker-compose exec database psql -U postgres -d bot_saas -f /docker-entrypoint-initdb.d/schema.sql

# 5. Проверить логи
docker-compose logs -f
```

### Продакшен сервер

#### Требования
| Ресурс | Значение |
|--------|----------|
| CPU | 4 vCPU (минимум) |
| RAM | 16 ГБ (256 МБ на контейнер бота + запас) |
| Disk | 100 ГБ NVMe |
| ОС | Ubuntu 22.04 LTS |

#### Чек-лист настройки сервера

```bash
# 1. Обновить систему
sudo apt update && sudo apt upgrade -y

# 2. Установить Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 3. Установить Docker Compose
sudo apt install docker-compose-plugin -y

# 4. Настроить фаервол
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# 5. Настроить автозапуск
sudo systemctl enable docker
sudo systemctl start docker

# 6. Настроить бэкапы (cron)
# 0 3 * * * pg_dump -U postgres bot_saas > /backups/db_$(date +\%F).sql
```

#### SSL сертификат (Let's Encrypt)
```bash
# Установить certbot
sudo apt install certbot python3-certbot-nginx -y

# Получить сертификат
sudo certbot --nginx -d api.yourdomain.com

# Автообновление (добавить в cron)
# 0 0 1 * * certbot renew --quiet
```

### Резервное копирование

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_DIR="/backups/$DATE"

mkdir -p $BACKUP_DIR

# Бэкап БД
docker-compose exec -T database pg_dump -U postgres bot_saas > $BACKUP_DIR/db.sql

# Бэкап томов Docker
tar -czf $BACKUP_DIR/volumes.tar.gz /var/lib/docker/volumes

# Сжатие
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
rm -rf $BACKUP_DIR

# Загрузка в S3 (опционально)
aws s3 cp $BACKUP_DIR.tar.gz s3://your-backup-bucket/

# Удаление старых бэкапов (> 30 дней)
find /backups -name "*.tar.gz" -mtime +30 -delete
```

---

## 🔐 Безопасность

### Токены ботов
```python
# Шифрование токенов перед сохранением в БД
from cryptography.fernet import Fernet

class TokenEncryption:
    def __init__(self, key: bytes):
        self.fernet = Fernet(key)
    
    def encrypt(self, token: str) -> str:
        return self.fernet.encrypt(token.encode()).decode()
    
    def decrypt(self, encrypted_token: str) -> str:
        return self.fernet.decrypt(encrypted_token.encode()).decode()
```

### Вебхуки Telegram
```python
# Валидация секретного токена вебхука
@app.post("/webhook/{bot_id}")
async def webhook(
    request: Request,
    bot_id: UUID,
    x_telegram_bot_api_secret_token: str = Header(...)
):
    expected_token = get_secret_token_for_bot(bot_id)
    if x_telegram_bot_api_secret_token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid secret token")
    
    # Обработка вебхука...
```

### 152-ФЗ требования
- [ ] Серверы расположены в РФ (Yandex Cloud / Selectel / Timeweb)
- [ ] Политика конфиденциальности на сайте
- [ ] Оферта для пользователей
- [ ] Логирование доступа к персональным данным
- [ ] Возможность экспорта/удаления данных по запросу пользователя

### Защита от злоупотреблений
| Угроза | Защита |
|--------|--------|
| DDoS | Rate limiting в nginx |
| SQL Injection | Параметризованные запросы (asyncpg) |
| XSS | Санитизация ввода в боте |
| Token leak | Шифрование в БД, доступ по ролям |
| Container escape | Изолированные сети Docker, non-root user |

---

## ✅ Чек-листы

### Чек-лист запуска нового бота
- [ ] Мастер создал бота через @BotFather
- [ ] Мастер отправил токен в PlatformBot
- [ ] Токен зашифрован и сохранён в БД
- [ ] Factory Service создал контейнер из шаблона
- [ ] Webhook установлен (ngrok или продакшен домен)
- [ ] Webhook URL проверен: `python3 scripts/set-bot-webhook.py {token} get`
- [ ] Конфиг загружен из БД (услуги, график)
- [ ] Бот ответил на /start
- [ ] Мастер получил уведомление об успехе

### Чек-лист записи клиента
- [ ] Клиент нажал /start в боте мастера
- [ ] Бот показал меню услуг
- [ ] Клиент выбрал услугу
- [ ] Бот показал доступные слоты
- [ ] Клиент выбрал время
- [ ] Проверка наложения в БД (нет ли другой записи)
- [ ] Запись сохранена со статусом `pending`
- [ ] Клиент получил подтверждение
- [ ] Мастер получил уведомление
- [ ] Напоминание запланировано в очереди

### Чек-лист отправки напоминания
- [ ] Notification Service проверяет очередь каждые 5 минут
- [ ] Найдены уведомления с `send_at <= NOW()`
- [ ] Бот отправляет сообщение клиенту
- [ ] Статус уведомления обновлён на `sent`
- [ ] Ошибка logged в `system_logs`

### Чек-лист продления подписки
- [ ] Billing Service проверяет `expires_at` ежедневно
- [ ] За 3 дня до истечения — уведомление мастеру
- [ ] Мастер получает ссылку на оплату
- [ ] Оплата прошла через ЮKassa
- [ ] Вебхук обновил `expires_at` в БД
- [ ] Мастер получил подтверждение

---

## 📎 Приложения

### Переменные окружения (.env.example)
```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@database:5432/bot_saas
REDIS_URL=redis://redis:6379/0

# Platform Bot
PLATFORM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
PLATFORM_BOT_WEBHOOK_SECRET=your_secret_token_here

# Encryption
ENCRYPTION_KEY=your_fernet_key_here

# Factory Service
DOCKER_HOST=unix:///var/run/docker.sock
BOT_TEMPLATE_IMAGE=telegram-bot-saas/bot-template:latest

# Billing
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key

# Monitoring
PROMETHEUS_URL=http://prometheus:9090
GRAFANA_URL=http://grafana:3000

# Server
SERVER_DOMAIN=api.yourdomain.com
SSL_CERT_PATH=/etc/letsencrypt/live/api.yourdomain.com/fullchain.pem
SSL_KEY_PATH=/etc/letsencrypt/live/api.yourdomain.com/privkey.pem
```

### Полезные команды Docker
```bash
# Просмотр логов конкретного сервиса
docker-compose logs -f platform-bot

# Перезапуск сервиса
docker-compose restart factory-service

# Вход в контейнер
docker-compose exec platform-bot bash

# Просмотр запущенных контейнеров ботов
docker ps --filter "label=service=telegram-bot"

# Очистка старых образов
docker image prune -a

# Бэкап БД
docker-compose exec database pg_dump -U postgres bot_saas > backup.sql

# Webhook команды
python3 scripts/set-bot-webhook.py {TOKEN} get              # Проверить webhook
python3 scripts/set-bot-webhook.py {TOKEN} delete           # Удалить webhook
python3 scripts/update-all-webhooks.py                      # Обновить webhook всех ботов
```

### Ссылки на документацию
- [aiogram 3.x Docs](https://docs.aiogram.dev/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Docs](https://docs.sqlalchemy.org/)
- [Docker SDK for Python](https://docker-py.readthedocs.io/)
- [YooKassa API](https://yookassa.ru/developers/api)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Webhook Setup Guide](./WEBHOOK_SETUP.md) - Подробная документация по webhook
- [MVP Checklist](./MVP_CHECKLIST.md) - Чек-лист готовности MVP

---

## 📝 Заметки

> **Идея для улучшения:** Добавить возможность экспорта записей в Google Calendar / Яндекс.Календарь через OAuth.

> **Риск:** При 100+ ботах может быть высокая нагрузка на БД. Решение: кэширование конфига бота в Redis, репликация БД.
