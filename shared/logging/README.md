# Shared Logging System

Централизованная система логирования для всех сервисов Telegram Bot SaaS.

---

## 📋 Функциональность

### ✅ Реализовано:
1. **Структурированное логирование** (JSON format)
2. **Log Rotation** (10 MB per file, 5 backups)
3. **Centralized API** для управления логами
4. **Фильтрация и поиск** логов
5. **Статистика по логам** (по уровням и сервисам)
6. **Экспорт логов** (JSON и CSV)
7. **Sentry интеграция** для error tracking
8. **Database логирование** (опционально)

### 📦 Компоненты:

#### config.py
Основной модуль логирования:
- `StructuredLogger` - основной класс логгера
- `JsonFormatter` - форматирование логов в JSON
- `DatabaseLogHandler` - запись логов в БД
- `setup_logging()` - удобная функция инициализации

#### models.py
Pydantic модели для Logging API:
- LogEntry - отдельная запись лога
- LogQuery - параметры запроса
- LogStats - статистика
- LogExportRequest - запрос на экспорт

#### api.py
FastAPI endpoint'ы для управления логами:
- GET /logs - получение логов с фильтрацией
- GET /stats - статистика логов
- DELETE /cleanup - удаление старых логов
- GET /export - экспорт логов
- GET /services - список сервисов
- GET /levels - доступные уровни

---

## 🚀 Использование

### Базовое использование:

```python
from shared.logging import setup_logging

# Настройка логгера
logger = setup_logging(
    service_name="my-service",
    level="INFO",           # DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_format="json",      # json, text, structured
    log_file="/var/log/my-service/app.log",
    log_to_db=False,        # True для записи в БД
    sentry_dsn="https://sentry.io/..."  # Sentry DSN (опционально)
)

# Использование
logger.info("Service started successfully")
logger.error("Failed to process request", exception=e)
logger.warning("Rate limit approaching")
```

### С контекстом:

```python
logger.info("User action completed",
            user_id=123,
            action="booking_created",
            service_id="abc-123",
            duration_seconds=5.2)

logger.error("Database connection failed",
            exception=e,
            query=sql_query,
            retries=3)
```

### Разные уровни логирования:

```python
logger.debug("Detailed debug information",
            variable=value,
            execution_time_ms=123)

logger.info("Informational messages",
            user_id=user.id,
            action="login")

logger.warning("Warning messages",
            rate_limit_used="95%",
            message="Approaching limit")

logger.error("Error messages",
            error_code="DB_CONNECTION_FAILED",
            error_message=str(e),
            context={"operation": "db_query"})

logger.critical("Critical failures",
            service_unavailable=True,
            error=str(e))
```

---

## 🌐 Logging API Endpoint'ы

### Получить логи:

```bash
GET /api/v1/logs

Query parameters:
- level: DEBUG|INFO|WARNING|ERROR|CRITICAL (опционально)
- service: platform-bot|notification-service (опционально)
- start_date: 2024-01-01T00:00:00Z (опционально)
- end_date: 2024-01-31T23:59:59Z (опционально)
- limit: 100 (default)
- offset: 0 (default)
- search: "error message" (опционально)

# Пример
curl "http://localhost:8000/api/v1/logs?level=ERROR&service=platform-bot&limit=50"
```

### Статистика:

```bash
GET /api/v1/logs/stats

# Возвращает:
{
  "total_logs": 1234,
  "by_level": {
    "INFO": 800,
    "ERROR": 34,
    "WARNING": 400
  },
  "by_service": {
    "platform-bot": {
      "total_logs": 500,
      "error_count": 10,
      "warning_count": 50,
      "last_error": null,
      "last_error_time": null
    }
  },
  "time_range": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-01-31T23:59:59Z"
  }
}
```

### Экспорт логов:

```bash
GET /api/v1/logs/export?format=json&service=platform-bot
GET /api/v1/logs/export?format=csv&level=ERROR&start_date=2024-01-01
```

### Очистка старых логов:

```bash
DELETE /api/v1/logs/cleanup

Body:
{
  "older_than_days": 30
}
```

---

## 🗄️ Интеграция с Sentry

Для использования Sentry error tracking:

```python
import os
from shared.logging import setup_logging

logger = setup_logging(
    service_name="my-service",
    sentry_dsn=os.getenv("SENTRY_DSN")
    # Автоматически будут отправляться ERROR и CRITICAL в Sentry
)
```

### Переменные окружения:

```bash
SENTRY_DSN=https://sentry.io/projects/your-project/dsn
SENTRY_ENVIRONMENT=production
SENTRY_RELEASE=1.0.0
```

---

## 📊 JSON формат лога:

```json
{
  "timestamp": "2024-03-15T18:30:45.123Z",
  "level": "INFO",
  "service": "notification-service",
  "logger": "worker",
  "function": "process_notifications",
  "line": 64,
  "message": "Processing 1 pending notifications",
  "extra": {
    "count": 1,
    "service": "notification-service"
  }
}
```

---

## 🔍 Мониторинг и аналитика

### Live мониторинг:

1. **Просмотр логов в реальном времени**:
   ```bash
   tail -f /var/log/notification-service/app.log
   # Или через API:
   curl "http://localhost:8000/api/v1/logs?limit=10" --watch
   ```

2. **Dashboard статистики**:
   ```bash
   curl "http://localhost:8000/api/v1/logs/stats"
   ```

3. **Error tracking**:
   - Sentry dashboard: https://sentry.io/
   - Автоматическая отправка stack traces
   - Alert'ы по ошибкам

### Метрики для отслеживания:

- **Error Rate**: кол-во ошибок в минуту/час
- **Service Availability**: процент успешных запросов
- **Response Times**: среднее время ответа
- **Database Connection Pool**: использовано подключений
- **Memory Usage**: потребление памяти сервисом

---

## 🛠️ Конфигурация в Docker

### Добавить в docker-compose.yml:

```yaml
logging-service:
  environment:
    LOG_LEVEL: INFO
    LOG_FORMAT: json
    LOG_FILE_PATH: /var/log/notification-service/app.log
    LOG_TO_DB: false
    SENTRY_DSN: ${SENTRY_DSN}
  volumes:
    - ./logs:/var/log/notification-service
```

### Логирование в других сервисах:

```python
# notification-service/src/main.py
from shared.logging import setup_logging

logger = setup_logging(
    service_name="notification-service",
    level=os.getenv("LOG_LEVEL", "INFO"),
    log_format=os.getenv("LOG_FORMAT", "json"),
    log_file=os.getenv("LOG_FILE_PATH")
)

# Заменить все logger.info(...) на logger.info(...)
```

---

## 📝 Best Practices

### 1. Структурированное логирование:
```python
# ❌ Плохо
logger.info(f"User {user_id} created booking for service {service_id}")

# ✅ Хорошо
logger.info("User created booking",
            user_id=user_id,
            service_id=service_id,
            booking_time=datetime.utcnow())
```

### 2. Правильные уровни логирования:
- **DEBUG**: детальная отладочная информация
- **INFO**: нормальный поток выполнения
- **WARNING**: потенциальные проблемы
- **ERROR**: ошибки которые обработаны
- **CRITICAL**: критические ошибки требующие внимания

### 3. Контекст и метаданные:
```python
logger.info("API request processed",
            endpoint="/api/v1/users",
            method="GET",
            status_code=200,
            duration_ms=123,
            user_id=user.id,
            ip_address=request.client.host)
```

### 4. Безопасность:
- Не логировать пароли и токены
- Маскировать чувствительные данные:
  ```python
  logger.info("User authenticated",
              user_id=user.id,
              token="***masked***")
  ```
- Логировать только первые N символов больших сообщений

---

## 🔧 Troubleshooting

### Логи не пишутся:

1. Проверьте права доступа к директории логов
2. Проверьте свободное место на диске
3. Проверьте правильность пути LOG_FILE_PATH

### Sentry не работает:

1. Проверьте что SENTRY_DSN корректный
2. Проверьте сетевой доступ к Sentry
3. Убедитесь что sentry-sdk установлен: `pip install sentry-sdk[fastapi]`

### Логи в БД слишком большие:

1. Установите фильтрацию по уровню (только ERROR и CRITICAL)
2. Добавите автоматическую очистку через cron job
3. Используйте log rotation для файлового логирования

---

## 📞 Поддержка

Для проблем с логированием:
1. Проверьте Logs API endpoint'ы
2. Экспортируйте логи для анализа
3. Используйте Sentry dashboard для error tracking
4. Проверьте документацию сервиса

---

**Версия:** 1.0.0
**Последнее обновление:** 2026-03-15
