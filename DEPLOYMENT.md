# 🚀 Telegram Bot SaaS - Руководство по деплойменту

## 📋 Содержание

1. [Требования к серверу](#требования-к-серверу)
2. [Подготовка окружения](#подготовка-окружения)
3. [Конфигурация](#конфигурация)
4. [Деплоймент](#деплоймент)
5. [Настройка SSL](#настройка-ssl)
6. [Настройка webhook](#настройка-webhook)
7. [Мониторинг](#мониторинг)
8. [Бэкапы](#бэкапы)
9. [Безопасность](#безопасность)
10. [Troubleshooting](#troubleshooting)

---

## Требования к серверу

### Минимальные требования

| Ресурс | Значение | Описание |
|--------|----------|----------|
| CPU | 2 vCPU | Минимум для работы всех сервисов |
| RAM | 8 ГБ | 4 ГБ для сервисов + 4 ГБ для контейнеров ботов |
| Disk | 50 ГБ | Для БД, логов и контейнеров |
| OS | Ubuntu 22.04 LTS | Рекомендуемая ОС |

### Рекомендуемые требования

| Ресурс | Значение | Описание |
|--------|----------|----------|
| CPU | 4 vCPU | Для лучшей производительности |
| RAM | 16 ГБ | 256 МБ на контейнер бота + запас |
| Disk | 100 ГБ NVMe | Для масштабирования |
| OS | Ubuntu 22.04 LTS | Рекомендуемая ОС |

### Хостинг провайдеры

Рекомендуемые провайдеры для РФ и СНГ:
- **Timeweb** - timeweb.com
- **Selectel** - selectel.ru
- **Yandex Cloud** - cloud.yandex.ru
- **RuVDS** - ruvds.com

---

## Подготовка окружения

### 1. Обновление системы

```bash
# Обновить все пакеты
sudo apt update && sudo apt upgrade -y

# Установить необходимые пакеты
sudo apt install -y \
    curl \
    wget \
    git \
    unzip \
    htop \
    tmux \
    ufw \
    fail2ban
```

### 2. Установка Docker

```bash
# Добавить Docker GPG ключ
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Добавить Docker репозиторий
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Установить Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Добавить пользователя в группу docker
sudo usermod -aG docker $USER

# Проверить установку
docker --version
docker compose version
```

### 3. Настройка firewall

```bash
# Разрешить SSH
sudo ufw allow 22/tcp

# Разрешить HTTP и HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Включить firewall
sudo ufw enable

# Проверить статус
sudo ufw status
```

### 4. Настройка fail2ban

```bash
# Установить fail2ban
sudo apt install -y fail2ban

# Создать локальную конфигурацию
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

# Настроить fail2ban
sudo tee /etc/fail2ban/jail.local > /dev/null <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[ssh]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
EOF

# Перезапустить fail2ban
sudo systemctl restart fail2ban
sudo systemctl enable fail2ban
```

### 5. Настройка swap (опционально)

```bash
# Проверить наличие swap
free -h

# Создать swap файл 4 ГБ
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Добавить в fstab для автоматического монтирования
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Настроить swappiness
sudo sysctl vm.swappiness=10
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
```

---

## Конфигурация

### 1. Клонирование репозитория

```bash
# Клонировать репозиторий
git clone https://github.com/yourusername/telegram-bot-saas.git
cd telegram-bot-saas

# Создать папку для логов
mkdir -p logs
```

### 2. Создание .env файла

```bash
# Создать .env файл
cp .env.prod .env

# Редактировать .env файл
nano .env
```

### 3. Пример .env файла

```bash
# Database
DATABASE_URL=postgresql://postgres:secure_password@database:5432/bot_saas
REDIS_URL=redis://redis:6379/0

# Platform Bot
PLATFORM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
PLATFORM_BOT_WEBHOOK_SECRET=random_secret_string_here

# Security
ENCRYPTION_KEY=generate_with_python_-_cryptography_fernet_generate_key
JWT_SECRET_KEY=generate_jwt_secret_here

# Factory Service
DOCKER_HOST=unix:///var/run/docker.sock
BOT_TEMPLATE_IMAGE=telegram-bot-saas/bot-template:latest

# Server
SERVER_DOMAIN=api.yourdomain.com
NGROK_ENABLED=false
WEBHOOK_BASE_URL=https://api.yourdomain.com

# Admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure_password
ADMIN_EMAIL=admin@yourdomain.com

# Billing (опционально)
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key

# Monitoring (опционально)
PROMETHEUS_URL=http://prometheus:9090
GRAFANA_URL=http://grafana:3000

# Development
DEBUG=false
LOG_LEVEL=INFO
```

### 4. Генерация секретных ключей

```bash
# Генерация ключа шифрования
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Генерация JWT секретного ключа
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Генерация webhook секрета
python3 -c "import secrets; print(secrets.token_urlsafe(16))"
```

---

## Деплоймент

### 1. Сборка образов

```bash
# Собрать все образы
docker compose -f docker-compose.prod.yml build

# Или собрать только нужный сервис
docker compose -f docker-compose.prod.yml build platform-bot
```

### 2. Запуск сервисов

```bash
# Запустить все сервисы
docker compose -f docker-compose.prod.yml up -d

# Проверить статус
docker compose -f docker-compose.prod.yml ps

# Просмотреть логи
docker compose -f docker-compose.prod.yml logs -f
```

### 3. Применение миграций БД

```bash
# Применить схему БД
docker compose -f docker-compose.prod.yml exec -T database psql -U postgres -d bot_saas < database/schema.sql

# Или через Alembic
docker compose -f docker-compose.prod.yml exec alembic alembic upgrade head
```

### 4. Создание администратора

```bash
# Создать администратора через API
curl -X POST http://localhost:8000/api/v1/admin/create \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "secure_password",
    "email": "admin@yourdomain.com"
  }'
```

### 5. Проверка работы

```bash
# Проверить здоровье всех сервисов
docker compose -f docker-compose.prod.yml ps

# Проверить логи platform-bot
docker compose -f docker-compose.prod.yml logs -f platform-bot

# Проверить логи factory-service
docker compose -f docker-compose.prod.yml logs -f factory-service

# Проверить логи web-api
docker compose -f docker-compose.prod.yml logs -f web-api
```

---

## Настройка SSL

### 1. Настройка DNS

1. Купите домен (например, `yourdomain.com`)
2. Настройте DNS запись:
```
A    api.yourdomain.com    YOUR_SERVER_IP
```

3. Подождите пока DNS распространится (обычно 5-30 минут)

### 2. Установка Certbot

```bash
# Установить certbot
sudo apt install -y certbot python3-certbot-nginx

# Получить сертификат для домена
sudo certbot certonly --standalone -d api.yourdomain.com
```

### 3. Копирование сертификатов

```bash
# Создать папку для SSL сертификатов
mkdir -p nginx/ssl

# Скопировать сертификаты
sudo cp /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/api.yourdomain.com/privkey.pem nginx/ssl/

# Установить права
sudo chmod 644 nginx/ssl/fullchain.pem
sudo chmod 600 nginx/ssl/privkey.pem
```

### 4. Автообновление сертификатов

```bash
# Создать скрипт автообновления
sudo tee /usr/local/bin/renew-ssl.sh > /dev/null <<EOF
#!/bin/bash
certbot renew --quiet
cp /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem /path/to/nginx/ssl/
cp /etc/letsencrypt/live/api.yourdomain.com/privkey.pem /path/to/nginx/ssl/
docker compose -f /path/to/docker-compose.prod.yml restart nginx
EOF

# Сделать скрипт исполняемым
sudo chmod +x /usr/local/bin/renew-ssl.sh

# Добавить в cron для ежедневной проверки
(crontab -l 2>/dev/null; echo "0 0 * * * /usr/local/bin/renew-ssl.sh") | crontab -
```

---

## Настройка webhook

### 1. Обновление переменных окружения

```bash
# Обновить .env файл
nano .env

# Установить следующие переменные:
NGROK_ENABLED=false
SERVER_DOMAIN=api.yourdomain.com
WEBHOOK_BASE_URL=https://api.yourdomain.com
```

### 2. Настройка webhook для Platform Bot

```bash
# Установить webhook для Platform Bot
curl -X POST https://api.telegram.org/bot${PLATFORM_BOT_TOKEN}/setWebhook \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"https://api.yourdomain.com/webhook/platform\",
    \"secret_token\": \"${PLATFORM_BOT_WEBHOOK_SECRET}\"
  }"

# Проверить статус webhook
curl https://api.telegram.org/bot${PLATFORM_BOT_TOKEN}/getWebhookInfo
```

### 3. Обновление webhook для всех ботов

```bash
# Обновить webhook для всех существующих ботов
python3 scripts/update-all-webhooks.py

# Или вручную для конкретного бота
python3 scripts/set-bot-webhook.py {BOT_TOKEN} set https://api.yourdomain.com/webhook/{bot_id}
```

---

## Мониторинг

### 1. Просмотр логов

```bash
# Логи всех сервисов
docker compose -f docker-compose.prod.yml logs -f

# Логи конкретного сервиса
docker compose -f docker-compose.prod.yml logs -f platform-bot

# Логи за последние 100 строк
docker compose -f docker-compose.prod.yml logs --tail=100 platform-bot

# Логи с определенным временем
docker compose -f docker-compose.prod.yml logs --since 1h platform-bot
```

### 2. Статистика контейнеров

```bash
# Статистика в реальном времени
docker stats

# Статистика без потокового режима
docker stats --no-stream

# Статистика только для сервисов приложения
docker stats $(docker compose -f docker-compose.prod.yml ps -q)
```

### 3. Проверка здоровья сервисов

```bash
# Проверить здоровье Factory Service
curl http://localhost:8002/api/v1/factory/health

# Проверить здоровье Web API
curl http://localhost:8000/api/v1/health

# Проверить nginx
curl https://api.yourdomain.com/health
```

### 4. Настройка Prometheus и Grafana (опционально)

```bash
# Запустить мониторинг
docker compose -f docker-compose.prod.yml up -d prometheus grafana

# Доступ к Grafana
# URL: http://your-server:3000
# Логин: admin
# Пароль: admin (изменить при первом входе)
```

---

## Бэкапы

### 1. Настройка бэкапов БД

```bash
# Создать скрипт бэкапа
sudo tee /usr/local/bin/backup-db.sh > /dev/null <<EOF
#!/bin/bash

# Настройки
BACKUP_DIR="/backups/db"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
KEEP_DAYS=30

# Создать папку для бэкапов
mkdir -p \$BACKUP_DIR

# Бэкап БД
docker compose -f /path/to/docker-compose.prod.yml exec -T database pg_dump -U postgres bot_saas > \$BACKUP_DIR/bot_saas_\$DATE.sql

# Сжатие
gzip \$BACKUP_DIR/bot_saas_\$DATE.sql

# Удаление старых бэкапов
find \$BACKUP_DIR -name "*.sql.gz" -mtime +\$KEEP_DAYS -delete

echo "Backup completed: bot_saas_\$DATE.sql.gz"
EOF

# Сделать скрипт исполняемым
sudo chmod +x /usr/local/bin/backup-db.sh

# Добавить в cron для ежедневного бэкапа в 3:00
(crontab -l 2>/dev/null; echo "0 3 * * * /usr/local/bin/backup-db.sh") | crontab -
```

### 2. Настройка бэкапов Docker volumes

```bash
# Создать скрипт бэкапа volumes
sudo tee /usr/local/bin/backup-volumes.sh > /dev/null <<EOF
#!/bin/bash

# Настройки
BACKUP_DIR="/backups/volumes"
DATE=\$(date +%Y-%m-%d_%H-%M-%S)
KEEP_DAYS=7

# Создать папку для бэкапов
mkdir -p \$BACKUP_DIR

# Бэкап volumes
tar -czf \$BACKUP_DIR/volumes_\$DATE.tar.gz /var/lib/docker/volumes

# Удаление старых бэкапов
find \$BACKUP_DIR -name "*.tar.gz" -mtime +\$KEEP_DAYS -delete

echo "Backup completed: volumes_\$DATE.tar.gz"
EOF

# Сделать скрипт исполняемым
sudo chmod +x /usr/local/bin/backup-volumes.sh

# Добавить в cron для еженедельного бэкапа в воскресенье в 4:00
(crontab -l 2>/dev/null; echo "0 4 * * 0 /usr/local/bin/backup-volumes.sh") | crontab -
```

### 3. Восстановление из бэкапа

```bash
# Остановить сервисы
docker compose -f docker-compose.prod.yml down

# Восстановить БД из бэкапа
gunzip < /backups/db/bot_saas_2024-01-15_03-00-00.sql.gz | docker compose -f docker-compose.prod.yml exec -T database psql -U postgres bot_saas

# Восстановить volumes из бэкапа
tar -xzf /backups/volumes/volumes_2024-01-15.tar.gz -C /

# Запустить сервисы
docker compose -f docker-compose.prod.yml up -d
```

---

## Безопасность

### 1. Настройка SSH

```bash
# Отредактировать конфигурацию SSH
sudo nano /etc/ssh/sshd_config

# Изменить следующие настройки:
Port 2222                           # Изменить стандартный порт
PermitRootLogin no                   # Запретить вход root
PasswordAuthentication no            # Запретить аутентификацию по паролю
PubkeyAuthentication yes             # Разрешить аутентификацию по ключу

# Перезапустить SSH
sudo systemctl restart sshd
```

### 2. Настройка fail2ban

```bash
# Проверить статус fail2ban
sudo fail2ban-client status

# Проверить статус ssh jail
sudo fail2ban-client status ssh

# Разбанить IP (если нужно)
sudo fail2ban-client set ssh unbanip {IP_ADDRESS}
```

### 3. Настройка автоматического обновления

```bash
# Установить unattended-upgrades
sudo apt install -y unattended-upgrades

# Настроить автоматическое обновление
sudo dpkg-reconfigure --priority=low unattended-upgrades

# Проверить настройки
sudo cat /etc/apt/apt.conf.d/50unattended-upgrades
```

### 4. Настройка ротации логов

```bash
# Создать конфигурацию для ротации логов
sudo tee /etc/logrotate.d/telegram-bot-saas > /dev/null <<EOF
/path/to/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        docker compose -f /path/to/docker-compose.prod.yml restart platform-bot
    endscript
}
EOF
```

---

## Troubleshooting

### 1. Контейнеры не запускаются

```bash
# Проверить статус контейнеров
docker compose -f docker-compose.prod.yml ps

# Проверить логи контейнеров
docker compose -f docker-compose.prod.yml logs

# Перезапустить проблемный контейнер
docker compose -f docker-compose.prod.yml restart {service_name}

# Полностью пересоздать контейнер
docker compose -f docker-compose.prod.yml up -d --force-recreate {service_name}
```

### 2. Проблемы с подключением к БД

```bash
# Проверить статус контейнера БД
docker compose -f docker-compose.prod.yml ps database

# Проверить логи БД
docker compose -f docker-compose.prod.yml logs database

# Проверить подключение к БД
docker compose -f docker-compose.prod.yml exec database psql -U postgres -d bot_saas -c "SELECT 1"

# Проверить переменные окружения
docker compose -f docker-compose.prod.yml config | grep DATABASE_URL
```

### 3. Проблемы с webhook

```bash
# Проверить статус webhook
curl https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo

# Проверить доступность URL
curl https://api.yourdomain.com/webhook/platform

# Проверить логи nginx
docker compose -f docker-compose.prod.yml logs nginx

# Проверить конфигурацию nginx
docker compose -f docker-compose.prod.yml exec nginx nginx -t
```

### 4. Проблемы с SSL сертификатами

```bash
# Проверить дату истечения сертификата
sudo certbot certificates

# Продлить сертификаты вручную
sudo certbot renew

# Проверить права доступа к сертификатам
ls -la nginx/ssl/

# Перезапустить nginx
docker compose -f docker-compose.prod.yml restart nginx
```

### 5. Недостаточно места на диске

```bash
# Проверить использование диска
df -h

# Очистить Docker
docker system prune -a

# Удалить старые образы
docker image prune -a

# Удалить старые контейнеры
docker container prune

# Удалить старые volumes
docker volume prune
```

---

## Автоматизация деплоя

### Скрипт деплоя

```bash
# Создать скрипт деплоя
sudo tee /usr/local/bin/deploy.sh > /dev/null <<'EOF'
#!/bin/bash

set -e

# Настройки
PROJECT_DIR="/path/to/telegram-bot-saas"
BACKUP_DIR="/backups"
DATE=$(date +%Y-%m-%d_%H-%M-%S)

echo "Starting deployment at $DATE"

# Переход в папку проекта
cd $PROJECT_DIR

# Тянуть последние изменения
git pull origin main

# Бэкап БД перед деплоем
echo "Creating database backup..."
mkdir -p $BACKUP_DIR
docker compose -f docker-compose.prod.yml exec -T database pg_dump -U postgres bot_saas > $BACKUP_DIR/bot_saas_before_deploy_$DATE.sql

# Сборка образов
echo "Building Docker images..."
docker compose -f docker-compose.prod.yml build

# Остановка старых контейнеров
echo "Stopping old containers..."
docker compose -f docker-compose.prod.yml down

# Применение миграций
echo "Applying database migrations..."
docker compose -f docker-compose.prod.yml up -d database
sleep 10
docker compose -f docker-compose.prod.yml exec -T database psql -U postgres -d bot_saas < database/schema.sql

# Запуск новых контейнеров
echo "Starting new containers..."
docker compose -f docker-compose.prod.yml up -d

# Проверка здоровья
echo "Checking health..."
sleep 30
curl -f http://localhost:8000/api/v1/health || exit 1

echo "Deployment completed successfully!"
EOF

# Сделать скрипт исполняемым
sudo chmod +x /usr/local/bin/deploy.sh
```

---

## Полезные команды

### Работа с Docker

```bash
# Запустить все сервисы
docker compose -f docker-compose.prod.yml up -d

# Остановить все сервисы
docker compose -f docker-compose.prod.yml down

# Перезапустить сервис
docker compose -f docker-compose.prod.yml restart {service_name}

# Просмотр логов
docker compose -f docker-compose.prod.yml logs -f {service_name}

# Вход в контейнер
docker compose -f docker-compose.prod.yml exec {service_name} bash

# Удалить старые контейнеры
docker container prune

# Удалить старые образы
docker image prune -a
```

### Работа с БД

```bash
# Подключение к PostgreSQL
docker compose -f docker-compose.prod.yml exec database psql -U postgres -d bot_saas

# Выполнить SQL запрос
docker compose -f docker-compose.prod.yml exec database psql -U postgres -d bot_saas -c "SELECT * FROM bots;"

# Импорт данных
docker compose -f docker-compose.prod.yml exec -T database psql -U postgres bot_saas < data.sql

# Экспорт данных
docker compose -f docker-compose.prod.yml exec -T database pg_dump -U postgres bot_saas > data.sql
```

### Работа с Redis

```bash
# Подключение к Redis
docker compose -f docker-compose.prod.yml exec redis redis-cli

# Проверить ключи
KEYS *

# Получить значение
GET {key}

# Удалить ключ
DEL {key}
```

---

## Дополнительные ресурсы

- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Certbot Documentation](https://certbot.eff.org/docs/)

---

**Последнее обновление:** 2026-03-20
