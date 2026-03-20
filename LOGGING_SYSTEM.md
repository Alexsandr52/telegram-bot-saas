# 📊 Система логирования Telegram Bot SaaS

Централизованная система логирования для всех сервисов проекта.

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────┐
│              API Gateway (nginx)                    │
│           Logs, API, Webhook routing               │
└─────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ PlatformBot   │   │ Logging Svc   │   │ Notification Svc│
│              │   │               │   │                │
│ logs to DB   │   │ stores logs   │   │ logs to DB     │
└───────────────┘   └───────────────┘   └───────────────┘
        │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │  System Logs   │
                    │ + Indexes      │
                    └─────────────────┘
```

---

## 📦 Компоненты

### 1. Shared Logging Module (`shared/logging/`)

#### config.py
Основной модуль логирования:
- `StructuredLogger` - класс логгера с JSON форматированием
- `JsonFormatter` - форматтер для JSON вывода
- `DatabaseLogHandler` - запись логов в PostgreSQL
- `setup_logging()` - удобная функция инициализации

**Функции:**
```python
logger.debug(message, **kwargs)
logger.info(message, **kwargs)
logger.warning(message, **kwargs)
logger.error(message, **kwargs)
logger.critical(message, **kwargs)
```

#### api.py
FastAPI endpoint'ы для управления логами:
- `GET /api/v1/logs` - получение логов с фильтрацией
- `GET /api/v1/logs/stats` - статистика по логам
- `DELETE /api/v1/logs/cleanup` - очистка старых логов
- `GET /api/v1/logs/export` - экспорт в JSON/CSV
- `GET /api/v1/logs/services` - список сервисов с логами
- `GET /api/v1/logs/levels` - доступные уровни

#### models.py
Pydantic модели для API:
- `LogEntry` - модель записи лога
- `LogQuery` - параметры запроса
- `LogStats` - статистика
- `LogLevel` - enum уровней (DEBUG, INFO, WARNING, ERROR, CRITICAL)

---

## 🚀 Использование в сервисах

### В Platform Bot:

```python
# platform-bot/src/main.py
from shared.logging import setup_logging

logger = setup_logging(
    service_name="platform-bot",
    level=os.getenv("LOG_LEVEL", "INFO"),
    log_format=os.getenv("LOG_FORMAT", "json"),
    log_file=os.getenv("LOG_FILE_PATH", "/var/log/platform-bot/app.log"),
    log_to_db=True,  # Писать логи в БД
    sentry_dsn=os.getenv("SENTRY_DSN")
)

logger.info("Platform bot started")
logger.error("Failed to process message",
            message="Error processing",
            user_id=user.id,
            exception=e)
```

### В Notification Service:

```python
# notification-service/src/main.py
from shared.logging import setup_logging

logger = setup_logging(
    service_name="notification-service",
    level="INFO",
    log_format="json",
    log_file="/var/log/notification-service/app.log",
    log_to_db=True,
    sentry_dsn=os.getenv("SENTRY_DSN")
)

logger.info(f"Processing {count} notifications")
logger.error("Failed to send notification",
            notification_id=notif.id,
            error=str(e))
```

### В Web API:

```python
# web-api/src/main.py
from shared.logging import setup_logging

logger = setup_logging(
    service_name="web-api",
    level="INFO",
    log_format="json",
    log_file="/var/log/web-api/app.log",
    log_to_db=True,
    sentry_dsn=os.getenv("SENTRY_DSN")
)

logger.info("API request processed",
            endpoint="/api/v1/users",
            method="GET",
            status_code=200,
            duration_ms=123)
```

---

## 📊 Мониторинг

### HTTP Endpoint'ы:

| Endpoint | Описание | Пример |
|----------|-----------|---------|
| GET /api/v1/logs | Получить логи | `curl "http://localhost:8001/api/v1/logs?level=ERROR&limit=50"` |
| GET /api/v1/logs/stats | Статистика | `curl "http://localhost:8001/api/v1/logs/stats"` |
| GET /api/v1/logs/export | Экспорт | `curl "http://localhost:8001/api/v1/logs/export?format=csv"` |
| DELETE /api/v1/logs/cleanup | Очистка | `curl -X DELETE "http://localhost:8001/api/v1/logs/cleanup"` |

### Фильтры логов:
- **level**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **service**: platform-bot, notification-service, web-api, factory-service
- **start_date**: начало периода
- **end_date**: конец периода
- **search**: поиск в сообщениях
- **limit**: количество результатов (max 1000)
- **offset**: пагинация

---

## 🔧 Конфигурация

### Переменные окружения (.env):

```bash
# Logging Configuration
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json                  # json, text, structured
LOG_FILE_PATH=/var/log/my-service/app.log
LOG_TO_DB=true                  # Записывать логи в БД
SENTRY_DSN=https://sentry.io/...  # Sentry DSN (опционально)
```

### Docker Compose:

```yaml
my-service:
  environment:
    LOG_LEVEL: ${LOG_LEVEL:-INFO}
    LOG_FORMAT: ${LOG_FORMAT:-json}
    LOG_FILE_PATH: /var/log/my-service/app.log
    LOG_TO_DB: ${LOG_TO_DB:-true}
    SENTRY_DSN: ${SENTRY_DSN:-}
  volumes:
    - ./logs:/var/log/my-service
```

---

## 📈 Статистика и метрики

### Автоматически собираемые метрики:

1. **Количество логов по уровням**
   - ERROR count per minute
   - WARNING count per minute
   - Total logs count

2. **По сервисам**
   - Количество запросов
   - Error rate
   - Response time (если логируется)

3. **По времени**
   - Peak hours (когда больше всего логов)
   - Error trends
   - Service uptime

### Пример ответа `/api/v1/logs/stats`:

```json
{
  "total_logs": 12345,
  "by_level": {
    "INFO": 9000,
    "WARNING": 3000,
    "ERROR": 300,
    "CRITICAL": 45
  },
  "by_service": {
    "platform-bot": {
      "total_logs": 5000,
      "error_count": 150,
      "warning_count": 500
    },
    "notification-service": {
      "total_logs": 3000,
      "error_count": 50,
      "warning_count": 200
    }
  },
  "time_range": {
    "start": "2024-03-15T00:00:00Z",
    "end": "2024-03-15T23:59:59Z"
  }
}
```

---

## 🔍 Troubleshooting

### Проблема: Логи не пишутся

**Решения:**
1. Проверьте права доступа к директории логов
2. Убедитесь что диск не заполнен (`df -h`)
3. Проверьте что LOG_FILE_PATH корректный
4. Проверьте что LOG_TO_DB=true если нужно писать в БД

### Проблема: Логи в БД слишком большие

**Решения:**
1. Установите фильтрацию: `level=ERROR` или `level=CRITICAL`
2. Используйте автоматическую очистку через cron:
   ```bash
   # В cron: 0 3 * * *  curl -X DELETE "http://localhost:8001/api/v1/logs/cleanup?older_than_days=7"
   ```
3. Увеличьте интервал NOTIFICATION_CHECK_INTERVAL для меньше записей

### Проблема: Sentry не отправляет ошибки

**Решения:**
1. Проверьте что SENTRY_DSN корректный
2. Убедитесь что `sentry-sdk[fastapi]` установлен
3. Проверьте сетевой доступ к Sentry
4. Проверьте что Sentry project создан и active

---

## 🛡️ Безопасность логирования

### Правила:

1. **Никогда не логировать:**
   - Пароли пользователей
   - Токены доступа
   - Кредитные карты
   - PIN коды
   - Персональные данные в открытом виде

2. **Маскирование:**
   ```python
   # ❌ Плохо
   logger.info(f"User logged in with password: {password}")

   # ✅ Хорошо
   logger.info("User logged in", password="***masked***")

   # Для токенов
   token = "123456:ABCdef"  # Оставляем только первые 10 символов
   logger.info("User authenticated", token=token[:10] + "***")
   ```

3. **Email'ы:**
   ```python
   # Маскировать email
   email = "user@example.com"
   masked_email = email[:2] + "***" + "@" + email.split("@")[1]
   logger.info("User email", email=masked_email)
   ```

---

## 📞 Поддержка

Для проблем с логированием:

1. **API документация:** `http://localhost:8001/docs`
2. **Просмотр логов:** `GET /api/v1/logs` с фильтрами
3. **Экспорт для анализа:** `GET /api/v1/logs/export`
4. **Live мониторинг:**
   ```bash
   # Следить за ошибками в реальном времени
   curl -s "http://localhost:8001/api/v1/logs?level=ERROR" | jq .
   ```

---

## 🎯 Best Practices

### 1. Структурированное логирование
```python
# ✅ Правильно
logger.info("User action completed",
            user_id=user.id,
            action="booking_created",
            service_id=service.id)

# ❌ Неправильно
logger.info(f"User {user.id} completed action {action} for service {service.id}")
```

### 2. Используйте правильные уровни
- **DEBUG**: для разработки и отладки
- **INFO**: для нормального потока
- **WARNING**: для потенциальных проблем
- **ERROR**: для обработанных ошибок
- **CRITICAL**: для критических сбоев

### 3. Добавляйте контекст
```python
logger.error("Database query failed",
            query=sql_query,
            params=params,
            error=str(e),
            user_id=getattr(current_user, 'id', None))
```

### 4. Избегайте избыточного логирования
- Логируйте только важные события
- Не логируйте в циклах без флага
- Используйте `if logger.is_enabled()` для дорогих операций

---

## 📝 Примеры

### Platform Bot:
```python
logger.info("Bot command received",
            command="/start",
            user_id=telegram_id,
            username=username)
```

### Notification Service:
```python
logger.info("Processing notification",
            notification_id=notif.id,
            type=notif.type,
            recipient_id=client_id,
            attempts=notif.attempts)
```

### Web API:
```python
logger.info("API request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            user_id=user.id if user else None)
```

---

**Версия:** 1.0.0
**Последнее обновление:** 2026-03-15
