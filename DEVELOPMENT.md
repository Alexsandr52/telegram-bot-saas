# 📚 Telegram Bot SaaS - Документация для разработчиков

## 📋 Содержание

1. [Архитектура](#архитектура)
2. [Структура проекта](#структура-проекта)
3. [База данных](#база-данных)
4. [API эндпоинты](#api-эндпоинты)
5. [Переменные окружения](#переменные-окружения)
6. [Разработка](#разработка)
7. [Тестирование](#тестирование)
8. [Скрипты и утилиты](#скрипты-и-утилиты)

---

## Архитектура

### Микросервисная архитектура

Система состоит из нескольких микросервисов, каждый из которых отвечает за свою область:

```
┌─────────────────────────────────────────────────────────────┐
│                    Внешние сервисы                        │
│  Telegram API | ЮKassa | Google Calendar (future)         │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Nginx Gateway                        │
│  SSL termination, Routing, Rate limiting, Load balancing  │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  Platform Bot   │   │  Bot Template  │   │   Web Panel    │
│  (порт 8001)   │   │   (клон)       │   │  (порт 3000)   │
└─────────────────┘   └─────────────────┘   └─────────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Business Logic Layer                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐  │
│  │ Factory Svc  │ │  Web API     │ │ Notification Svc │  │
│  │  (порт 8002) │ │ (порт 8000)  │ │   (порт 8003)   │  │
│  └──────────────┘ └──────────────┘ └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   PostgreSQL    │   │     Redis       │   │  Logging Svc   │
│   (порт 5432)  │   │   (порт 6379)  │ │   (порт 8005)   │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

### Принципы архитектуры

1. **Изоляция:** Каждый бот мастера работает в отдельном Docker контейнере
2. **Масштабируемость:** Каждый микросервис можно масштабировать независимо
3. **Отказоустойчивость:** При падении одного бота другие продолжают работать
4. **Безопасность:** Шифрование токенов, секретные токены для webhook

---

## Структура проекта

### Platform Bot

```
platform-bot/
├── src/
│   ├── main.py                 # Точка входа
│   ├── handlers/               # Обработчики сообщений
│   │   ├── start.py            # /start команды
│   │   ├── connect_bot.py      # Подключение бота мастера
│   │   ├── services.py         # Управление услугами
│   │   ├── schedule.py         # Управление графиком
│   │   ├── appointments.py     # Просмотр записей
│   │   └── auth.py            # Аутентификация
│   ├── keyboards/              # Inline клавиатуры
│   ├── middlewares/            # Промежуточное ПО
│   └── utils/                  # Утилиты
│       ├── config.py           # Конфигурация
│       ├── db.py               # Работа с БД
│       ├── repositories.py     # Репозитории данных
│       └── encryption.py      # Шифрование токенов
```

### Factory Service

```
factory-service/
├── src/
│   ├── main.py
│   ├── api/                    # FastAPI роуты
│   │   ├── bots.py             # Управление ботами
│   │   ├── containers.py       # Контейнеры
│   │   └── health.py          # Health check
│   ├── docker/                 # Docker SDK обёртки
│   │   ├── manager.py          # Менеджер контейнеров
│   │   └── client.py          # Клиент Docker
│   └── models/                 # Pydantic модели
```

### Bot Template

```
bot-template/
├── src/
│   ├── main.py                 # Точка входа бота
│   ├── handlers/
│   │   ├── client_menu.py      # Меню клиента
│   │   ├── services.py         # Выбор услуги
│   │   ├── booking.py          # Запись на услугу
│   │   └── profile.py          # Профиль клиента
│   ├── keyboards/
│   ├── services/               # Бизнес-логика
│   │   ├── scheduler.py        # Генерация слотов
│   │   └── calendar.py         # Работа с датами
│   └── utils/
│       ├── config.py           # Загрузка конфига из БД
│       └── db.py               # Подключение к БД
```

### Web API

```
web-api/
├── src/
│   ├── main.py
│   ├── api/
│   │   ├── auth.py             # Аутентификация
│   │   ├── bots.py             # Управление ботами
│   │   ├── services.py         # Управление услугами
│   │   ├── schedules.py        # Управление графиком
│   │   └── appointments.py     # Записи
│   └── utils/
```

### Web Panel

```
web-panel/
├── index.html                 # Страница входа
├── dashboard.html             # Дашборд
└── static/
    ├── css/
    │   └── style.css
    └── js/
        ├── api.js              # API клиент
        ├── login.js           # Логика входа
        └── dashboard.js       # Логика дашборда
```

---

## База данных

### Схема БД

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
| bot_name | VARCHAR(255) | Название бота |
| business_name | VARCHAR(255) | Название бизнеса |
| container_status | VARCHAR(50) | Статус контейнера |
| container_id | VARCHAR(255) | ID Docker контейнера |
| webhook_url | VARCHAR(255) | URL вебхука |
| timezone | VARCHAR(50) | Часовой пояс |
| language | VARCHAR(10) | Язык |
| settings | JSONB | Дополнительные настройки |
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
| prepayment_percent | INTEGER | Процент предоплаты |
| photo_url | VARCHAR(500) | URL фото |
| is_active | BOOLEAN | Статус услуги |
| sort_order | INTEGER | Порядок отображения |
| settings | JSONB | Гибкие настройки |
| created_at | TIMESTAMPTZ | Дата создания |

#### schedules
| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID | Первичный ключ |
| bot_id | UUID | Ссылка на бота (FK) |
| day_of_week | INTEGER | День недели (0-6, 0 = Понедельник) |
| start_time | TIME | Начало работы |
| end_time | TIME | Конец работы |
| is_working_day | BOOLEAN | Рабочий день или выходной |
| break_start_time | TIME | Начало перерыва |
| break_end_time | TIME | Конец перерыва |

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
| price | DECIMAL(10,2) | Цена |
| prepayment_amount | DECIMAL(10,2) | Сумма предоплаты |
| client_comment | TEXT | Комментарий клиента |
| master_comment | TEXT | Комментарий мастера |
| confirmed_at | TIMESTAMPTZ | Дата подтверждения |
| completed_at | TIMESTAMPTZ | Дата завершения |
| cancelled_at | TIMESTAMPTZ | Дата отмены |
| created_at | TIMESTAMPTZ | Дата создания |
| updated_at | TIMESTAMPTZ | Дата обновления |

#### clients
| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID | Первичный ключ |
| bot_id | UUID | Ссылка на бота (FK) |
| telegram_id | BIGINT | ID в Telegram |
| username | VARCHAR(255) | Никнейм |
| first_name | VARCHAR(255) | Имя |
| last_name | VARCHAR(255) | Фамилия |
| phone | VARCHAR(20) | Телефон |
| email | VARCHAR(255) | Email |
| notes | TEXT | Заметки |
| total_visits | INTEGER | Всего визитов |
| total_spent | DECIMAL(10,2) | Всего потрачено |
| is_blocked | BOOLEAN | Заблокирован или нет |
| created_at | TIMESTAMPTZ | Дата создания |
| updated_at | TIMESTAMPTZ | Дата обновления |

#### subscriptions
| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID | Первичный ключ |
| master_id | UUID | Ссылка на мастера (FK) |
| plan | VARCHAR(50) | Тариф (free, pro, business) |
| status | VARCHAR(50) | Статус (active, expired, cancelled, pending) |
| bots_limit | INTEGER | Лимит ботов |
| appointments_limit | INTEGER | Лимит записей |
| starts_at | TIMESTAMPTZ | Дата начала |
| expires_at | TIMESTAMPTZ | Дата окончания |
| auto_renew | BOOLEAN | Авто продление |
| created_at | TIMESTAMPTZ | Дата создания |
| updated_at | TIMESTAMPTZ | Дата обновления |

#### notifications_queue
| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID | Первичный ключ |
| bot_id | UUID | Ссылка на бота (FK) |
| client_id | UUID | Ссылка на клиента (FK) |
| master_id | UUID | Ссылка на мастера (FK) |
| type | VARCHAR(50) | Тип уведомления |
| message | TEXT | Текст сообщения |
| send_at | TIMESTAMPTZ | Время отправки |
| status | VARCHAR(50) | Статус (pending, sent, failed) |
| attempts | INTEGER | Количество попыток |
| max_attempts | INTEGER | Максимум попыток |
| error_message | TEXT | Сообщение об ошибке |
| created_at | TIMESTAMPTZ | Дата создания |
| updated_at | TIMESTAMPTZ | Дата обновления |

### Индексы

```sql
-- Мастера
CREATE INDEX idx_masters_telegram_id ON masters(telegram_id);

-- Боты
CREATE INDEX idx_bots_master_id ON bots(master_id);
CREATE INDEX idx_bots_token ON bots(bot_token);
CREATE INDEX idx_bots_status ON bots(container_status);

-- Услуги
CREATE INDEX idx_services_bot_id ON services(bot_id);
CREATE INDEX idx_services_active ON services(bot_id) WHERE is_active = TRUE;

-- Расписание
CREATE INDEX idx_schedules_bot_id ON schedules(bot_id);

-- Записи (самый важный индекс для календаря)
CREATE INDEX idx_appointments_bot_time ON appointments(bot_id, start_time);
CREATE INDEX idx_appointments_status ON appointments(status);
CREATE INDEX idx_appointments_client_id ON appointments(client_id);

-- Клиенты
CREATE INDEX idx_clients_bot_id ON clients(bot_id);
CREATE INDEX idx_clients_telegram_id ON clients(telegram_id);

-- Подписки
CREATE INDEX idx_subscriptions_master_id ON subscriptions(master_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);

-- Уведомления
CREATE INDEX idx_notifications_send_at ON notifications_queue(send_at)
    WHERE status = 'pending';
CREATE INDEX idx_notifications_status ON notifications_queue(status);
```

### Виды (Views)

```sql
-- Активные подписки с количеством ботов
CREATE VIEW active_subscriptions_view AS
SELECT
    s.id,
    s.master_id,
    s.plan,
    s.status,
    s.expires_at,
    COUNT(b.id) AS active_bots_count
FROM subscriptions s
LEFT JOIN bots b ON b.master_id = s.master_id AND b.is_active = TRUE
WHERE s.status = 'active' AND s.expires_at > NOW()
GROUP BY s.id;

-- Записи на сегодня
CREATE VIEW today_appointments_view AS
SELECT
    a.id,
    a.bot_id,
    a.client_id,
    a.service_id,
    a.start_time,
    a.status,
    s.name AS service_name,
    c.first_name,
    c.last_name
FROM appointments a
JOIN services s ON s.id = a.service_id
JOIN clients c ON c.id = a.client_id
WHERE DATE(a.start_time) = CURRENT_DATE
    AND a.status IN ('pending', 'confirmed');

-- Статистика ботов
CREATE VIEW bot_statistics_view AS
SELECT
    b.id,
    b.bot_name,
    b.master_id,
    COUNT(DISTINCT a.client_id) AS total_clients,
    COUNT(a.id) AS total_appointments,
    SUM(a.price) AS total_revenue,
    COUNT(CASE WHEN a.status = 'confirmed' THEN 1 END) AS confirmed_appointments
FROM bots b
LEFT JOIN appointments a ON a.bot_id = b.id
WHERE b.is_active = TRUE
GROUP BY b.id;
```

---

## API эндпоинты

### Factory Service

#### Создать бота
```http
POST /api/v1/factory/bots/
Content-Type: application/json

{
  "master_id": "uuid",
  "bot_token": "encrypted_token",
  "bot_username": "my_master_bot"
}

Response:
{
  "bot_id": "uuid",
  "container_id": "abc123",
  "status": "running",
  "webhook_url": "https://api.platform.com/webhook/abc123"
}
```

#### Получить информацию о боте
```http
GET /api/v1/factory/bots/{id}/
```

#### Удалить бота
```http
DELETE /api/v1/factory/bots/{id}/
```

#### Перезапустить бота
```http
POST /api/v1/factory/bots/{id}/restart/
```

#### Health check
```http
GET /api/v1/factory/health/

Response:
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:00:00Z"
}
```

### Web API

#### Аутентификация
```http
POST /api/v1/auth/login/
Content-Type: application/json

{
  "auth_code": "123456"
}

Response:
{
  "token": "jwt_token",
  "master_id": "uuid",
  "expires_in": 86400
}
```

#### Список ботов
```http
GET /api/v1/bots/
Authorization: Bearer {token}

Response:
{
  "bots": [
    {
      "id": "uuid",
      "bot_name": "My Beauty Bot",
      "bot_username": "my_beauty_bot",
      "container_status": "running",
      "is_active": true
    }
  ]
}
```

#### Создать услугу
```http
POST /api/v1/services/
Authorization: Bearer {token}
Content-Type: application/json

{
  "bot_id": "uuid",
  "name": "Маникюр",
  "description": "Классический маникюр",
  "price": 1000.00,
  "duration_minutes": 60
}
```

#### Получить записи
```http
GET /api/v1/appointments/?bot_id={uuid}&date_from={date}&date_to={date}
Authorization: Bearer {token}
```

---

## Переменные окружения

### Критически важные

```bash
# Database
DATABASE_URL=postgresql://postgres:password@database:5432/bot_saas
REDIS_URL=redis://redis:6379/0

# Platform Bot
PLATFORM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
PLATFORM_BOT_WEBHOOK_SECRET=your_secret_token_here

# Security
ENCRYPTION_KEY=generate_with_python_-_cryptography_fernet_generate_key
JWT_SECRET_KEY=generate_jwt_secret_here

# Factory Service
DOCKER_HOST=unix:///var/run/docker.sock
BOT_TEMPLATE_IMAGE=telegram-bot-saas/bot-template:latest
```

### Опциональные

```bash
# Billing
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key

# Monitoring
PROMETHEUS_URL=http://prometheus:9090
GRAFANA_URL=http://grafana:3000

# Development
DEBUG=true
LOG_LEVEL=INFO

# Webhook
WEBHOOK_BASE_URL=https://api.yourdomain.com
NGROK_ENABLED=false
```

---

## Разработка

### Локальная разработка

```bash
# 1. Запустить все сервисы в development режиме
docker-compose up -d

# 2. Проверить статус сервисов
make health

# 3. Просмотреть логи конкретного сервиса
docker-compose logs -f platform-bot

# 4. Войти в контейнер
docker-compose exec platform-bot bash

# 5. Запустить тесты
docker-compose exec platform-bot pytest

# 6. Остановить сервисы
docker-compose down
```

### Отладка бота

```bash
# Просмотр логов платформенного бота
docker-compose logs -f platform-bot

# Просмотр логов конкретного бота мастера
docker logs bot_{container_id} -f

# Проверка webhook
python3 scripts/set-bot-webhook.py {BOT_TOKEN} get

# Тестирование webhook
python3 scripts/webhook-tester.py {WEBHOOK_URL}
```

### Релиз новой версии

```bash
# 1. Собрать образы
docker-compose build

# 2. Перезапустить сервисы с новыми образами
docker-compose up -d --force-recreate

# 3. Применить миграции БД
docker-compose exec database psql -U postgres -d bot_saas -f /migrations/{migration_file}
```

---

## Тестирование

### Unit тесты

```bash
# Запуск unit тестов для platform-bot
docker-compose exec platform-bot pytest tests/unit/

# Запуск unit тестов для web-api
docker-compose exec web-api pytest tests/unit/
```

### Интеграционные тесты

```bash
# Запуск интеграционных тестов
docker-compose exec web-api pytest tests/integration/

# Запуск всех тестов
docker-compose exec web-api pytest
```

### E2E тесты

```bash
# Запуск end-to-end тестов
python3 scripts/e2e-tests.py
```

---

## Скрипты и утилиты

### Webhook скрипты

```bash
# Настройка ngrok для локальной разработки
./scripts/setup-ngrok.sh

# Установка webhook для бота
python3 scripts/set-bot-webhook.py {BOT_TOKEN} set {WEBHOOK_URL}

# Проверка статуса webhook
python3 scripts/set-bot-webhook.py {BOT_TOKEN} get

# Удаление webhook
python3 scripts/set-bot-webhook.py {BOT_TOKEN} delete

# Обновление webhook для всех ботов
python3 scripts/update-all-webhooks.py

# Переключение между webhook и polling
python3 scripts/toggle-webhook-mode.py {BOT_TOKEN} polling
```

### Бэкапы

```bash
# Бэкап базы данных
make db-backup

# Или вручную
docker-compose exec -T database pg_dump -U postgres bot_saas > backup.sql

# Восстановление из бэкапа
docker-compose exec -T database psql -U postgres bot_saas < backup.sql
```

### Мониторинг

```bash
# Проверка здоровья всех сервисов
make health

# Просмотр логов всех сервисов
make logs

# Статистика Docker
docker stats

# Информация о контейнере
docker inspect {container_id}
```

---

## Полезные команды

### Работа с Docker

```bash
# Запустить все сервисы
docker-compose up -d

# Остановить все сервисы
docker-compose down

# Перезапустить сервис
docker-compose restart {service_name}

# Просмотр логов
docker-compose logs -f {service_name}

# Вход в контейнер
docker-compose exec {service_name} bash

# Удалить старые контейнеры
docker container prune

# Удалить старые образы
docker image prune -a
```

### Работа с БД

```bash
# Подключение к PostgreSQL
docker-compose exec database psql -U postgres -d bot_saas

# Выполнить SQL запрос
docker-compose exec database psql -U postgres -d bot_saas -c "SELECT * FROM bots;"

# Импорт данных
docker-compose exec -T database psql -U postgres bot_saas < data.sql

# Экспорт данных
docker-compose exec -T database pg_dump -U postgres bot_saas > data.sql
```

### Работа с Redis

```bash
# Подключение к Redis
docker-compose exec redis redis-cli

# Проверить ключи
KEYS *

# Получить значение
GET {key}

# Удалить ключ
DEL {key}
```

---

## Troubleshooting

### Бот не отвечает

1. Проверить статус контейнера:
```bash
docker ps | grep {bot_container_id}
```

2. Проверить логи бота:
```bash
docker logs {bot_container_id} -f
```

3. Проверить webhook:
```bash
python3 scripts/set-bot-webhook.py {BOT_TOKEN} get
```

### Ошибка подключения к БД

1. Проверить статус БД:
```bash
docker-compose ps database
```

2. Проверить подключение:
```bash
docker-compose exec database psql -U postgres -d bot_saas -c "SELECT 1"
```

3. Проверить переменные окружения:
```bash
docker-compose exec platform-bot env | grep DATABASE_URL
```

### Webhook не работает

1. Проверить статус webhook:
```bash
python3 scripts/set-bot-webhook.py {BOT_TOKEN} get
```

2. Проверить доступность URL:
```bash
curl {WEBHOOK_URL}
```

3. Проверить логи nginx:
```bash
docker-compose logs -f nginx
```

---

## Дополнительные ресурсы

- [aiogram 3.x Documentation](https://docs.aiogram.dev/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Docker Documentation](https://docs.docker.com/)
- [Redis Documentation](https://redis.io/documentation)

---

**Последнее обновление:** 2026-03-20
