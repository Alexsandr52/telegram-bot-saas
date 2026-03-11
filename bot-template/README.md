# Bot Template - Шаблон бота мастера

Этот бот предназначен для мастеров, которые хотят принимать записи от клиентов через Telegram.

## Возможности

- 📋 **Каталог услуг** - показывает все услуги мастера
- 📅 **Выбор даты** - клиент выбирает удобную дату
- 🕐 **Выбор времени** - показывает доступные слоты
- ✅ **Запись** - создаёт запись в БД
- 👤 **Профиль клиента** - история записей

## Команды

- `/start` - Главное меню
- `/help` - Справка
- `/about` - Информация о мастере
- `/catalog` (или кастомная, например `/c`) - Услуги и запись

## Структура

```
bot-template/
├── Dockerfile
├── requirements.txt
├── .env.example
└── src/
    ├── main.py              # Точка входа
    ├── handlers/            # Обработчики
    │   ├── client_menu.py   # Основные команды
    │   ├── services.py       # Выбор услуги и даты
    │   ├── booking.py        # Запись
    │   └── profile.py        # Профиль
    ├── keyboards/           # Клавиатуры
    ├── utils/
    │   ├── config.py         # Загрузка конфига из БД
    │   └── db.py             # Операции с БД
```

## Тестирование локально

### 1. Создай тестового бота

```
1. Открой @BotFather
2. /newbot
3. Придумай название: "Test Master Bot"
4. Скопируй токен
```

### 2. Добавь тестовые данные в БД

```sql
-- 1. Создай тестового мастера
INSERT INTO masters (telegram_id, username, full_name, is_active)
VALUES (123456789, 'test_user', 'Test Master', true);

-- 2. Создай тестового бота
INSERT INTO bots (master_id, bot_token, bot_username, bot_name, container_status)
VALUES (
    (SELECT id FROM masters WHERE telegram_id = 123456789),
    'encrypted_token_here',
    'TestMasterBot',
    'Test Master',
    'stopped'
);

-- 3. Добавь услуги
INSERT INTO services (bot_id, name, description, price, duration_minutes, is_active)
SELECT 
    id,
    'Стрижка мужская',
    'Классическая мужская стрижка',
    1500,
    60,
    true
FROM bots WHERE bot_username = 'TestMasterBot';

INSERT INTO services (bot_id, name, description, price, duration_minutes, is_active)
SELECT 
    id,
    'Окрашивание',
    'Окрашивание волос',
    3000,
    120,
    true
FROM bots WHERE bot_username = 'TestMasterBot';

-- 4. Настрой график (Пн-Пт 9:00-18:00)
INSERT INTO schedules (bot_id, day_of_week, start_time, end_time, is_working_day)
SELECT id, 0, '09:00:00', '18:00:00', true FROM bots WHERE bot_username = 'TestMasterBot';
INSERT INTO schedules (bot_id, day_of_week, start_time, end_time, is_working_day)
SELECT id, 1, '09:00:00', '18:00:00', true FROM bots WHERE bot_username = 'TestMasterBot';
INSERT INTO schedules (bot_id, day_of_week, start_time, end_time, is_working_day)
SELECT id, 2, '09:00:00', '18:00:00', true FROM bots WHERE bot_username = 'TestMasterBot';
INSERT INTO schedules (bot_id, day_of_week, start_time, end_time, is_working_day)
SELECT id, 3, '09:00:00', '18:00:00', true FROM bots WHERE bot_username = 'TestMasterBot';
INSERT INTO schedules (bot_id, day_of_week, start_time, end_time, is_working_day)
SELECT id, 4, '09:00:00', '18:00:00', true FROM bots WHERE bot_username = 'TestMasterBot';
```

### 3. Запусти бота

```bash
# Из директории bot-template
cp .env.example .env

# Редактируй .env
# BOT_ID=uuid-бота-из-БД
# BOT_TOKEN=токен-от-BotFather

python -m pip install -r requirements.txt
python src/main.py
```

### 4. Тестирование

```
1. Открой бота в Telegram
2. Напиши /start
3. Выбери услугу
4. Выбери дату
5. Выбери время
6. Подтверди запись
```

## Кастомизация команд

Мастер может настроить свои команды в БД через `bots.settings` JSONB:

```json
{
  "custom_commands": [
    {
      "command": "c",
      "description": "Услуги",
      "handler_type": "catalog",
      "enabled": true
    },
    {
      "command": "info",
      "description": "О нас",
      "handler_type": "about",
      "enabled": true
    }
  ]
}
```

## Запись в БД

При подтверждении записи создаётся запись в таблице `appointments`:

- `bot_id` - ID бота
- `client_id` - ID клиента (создаётся автоматически)
- `service_id` - ID выбранной услуги
- `start_time` - Начало записи
- `end_time` - Конец записи
- `price` - Цена услуги
- `status` - `pending` (в дальнейшем меняется на `confirmed`/`completed`/`cancelled`)

## Отладка

```python
# Посмотреть загруженный конфиг
config_manager = get_config_manager()
config = config_manager.config
print(f"Services: {len(config.services)}")
print(f"Schedule days: {len(config.schedule)}")

# Проверить доступные слоты
db = get_database()
slots = await db.get_available_slots(service_id, date)
for slot in slots:
    print(f"{slot['start_time']} - {slot['is_available']}")
```
