# Quick Start Guide

## Быстрый запуск БД для Telegram Bot SaaS

### 1. Создайте файл .env

```bash
make env-setup
# или вручную
cp .env.example .env
```

### 2. Запустите БД

```bash
make up
# или
docker-compose up -d
```

### 3. Проверьте статус

```bash
make health
```

### 4. Доступ к БД

#### psql (CLI)
```bash
make db-shell
```

#### pgAdmin (Web UI)
- URL: http://localhost:5050
- Email: admin@botsaas.local
- Password: admin123

#### Redis Commander
- URL: http://localhost:8082

### 5. Основные команды

```bash
make logs          # Логи всех сервисов
make db-backup     # Бэкап БД
make db-restore    # Восстановление из бэкапа
make db-shell      # PostgreSQL shell
make redis-shell   # Redis CLI
make down          # Остановить все сервисы
make info          # Информация о проекте
```

### Структура БД

- **masters** - Мастера (пользователи платформы)
- **bots** - Боты мастеров
- **clients** - Клиенты
- **services** - Услуги
- **appointments** - Записи
- **schedules** - График работы
- **subscriptions** - Подписки
- **payments** - Платежи
- **notifications_queue** - Очередь уведомлений

### Подключение из Python

```python
import asyncpg

conn = await asyncpg.connect(
    host='localhost',
    port=5432,
    user='postgres',
    password='postgres',
    database='bot_saas'
)
```

### Или SQLAlchemy

```python
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    'postgresql+asyncpg://postgres:postgres@localhost:5432/bot_saas'
)
```

### Следующие шаги

1. Изучите `database/README.md` для детальной документации
2. Посмотрите `database/schema.sql` для понимания структуры БД
3. Используйте `Makefile` для удобного управления

### Полезные запросы

#### Получить всех мастеров
```sql
SELECT * FROM masters;
```

#### Получить боты мастера
```sql
SELECT * FROM bots WHERE master_id = 'master-uuid';
```

#### Получить записи на сегодня
```sql
SELECT * FROM today_appointments_view;
```

#### Проверить доступность слота
```sql
SELECT check_slot_availability(
    'bot-uuid'::UUID,
    '2025-01-15 10:00:00'::TIMESTAMPTZ,
    '2025-01-15 11:00:00'::TIMESTAMPTZ
);
```

---

**Документация:** [database/README.md](database/README.md)
**Полная документация:** [README.md](README.md)
