# ============================================
# Telegram Bot SaaS - Makefile
# Convenient commands for development
# ============================================

.PHONY: help build up down restart logs db-shell db-backup db-restore clean install test lint

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# ============================================
# Help
# ============================================
help: ## Show this help message
	@echo "$(BLUE)Telegram Bot SaaS - Development Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Usage:$(NC)"
	@echo "  make [target]"
	@echo ""
	@echo "$(GREEN)Available targets:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

# ============================================
# Docker Commands
# ============================================
build: ## Build all Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	docker-compose build

up: ## Start all services
	@echo "$(BLUE)Starting all services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)All services started!$(NC)"
	@echo "$(BLUE)PostgreSQL:$(NC) localhost:5432"
	@echo "$(BLUE)Redis:$(NC) localhost:6379"
	@echo "$(BLUE)pgAdmin:$(NC) http://localhost:5050"
	@echo "$(BLUE)Redis Commander:$(NC) http://localhost:8082"

down: ## Stop all services
	@echo "$(BLUE)Stopping all services...$(NC)"
	docker-compose down
	@echo "$(GREEN)All services stopped!$(NC)"

restart: ## Restart all services
	@echo "$(BLUE)Restarting all services...$(NC)"
	docker-compose restart
	@echo "$(GREEN)Services restarted!$(NC)"

logs: ## Show logs from all services
	docker-compose logs -f

logs-db: ## Show database logs
	docker-compose logs -f database

logs-redis: ## Show Redis logs
	docker-compose logs -f redis

# ============================================
# Database Commands
# ============================================
db-shell: ## Open PostgreSQL shell
	@echo "$(BLUE)Opening PostgreSQL shell...$(NC)"
	docker-compose exec database psql -U postgres -d bot_saas

db-backup: ## Backup database to file
	@echo "$(BLUE)Creating database backup...$(NC)"
	@mkdir -p backups
	docker-compose exec -T database pg_dump -U postgres bot_saas | gzip > backups/backup_$$(date +%Y%m%d_%H%M%S).sql.gz
	@echo "$(GREEN)Backup created in backups/ directory$(NC)"

db-restore: ## Restore database from backup (usage: make db-restore FILE=backups/backup_20250115.sql.gz)
	@if [ -z "$(FILE)" ]; then \
		echo "$(RED)Error: Please specify FILE parameter$(NC)"; \
		echo "$(YELLOW)Usage: make db-restore FILE=backups/backup_20250115.sql.gz$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Restoring database from $(FILE)...$(NC)"
	gunzip -c $(FILE) | docker-compose exec -T database psql -U postgres bot_saas
	@echo "$(GREEN)Database restored!$(NC)"

db-reset: ## Reset database (WARNING: deletes all data)
	@echo "$(RED)WARNING: This will delete all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(BLUE)Resetting database...$(NC)"; \
		docker-compose down -v; \
		docker-compose up -d database; \
		echo "$(GREEN)Database reset complete!$(NC)"; \
	else \
		echo "$(YELLOW)Aborted.$(NC)"; \
	fi

db-migrate: ## Run database migrations
	@echo "$(BLUE)Running migrations...$(NC)"
	cd database && alembic upgrade head
	@echo "$(GREEN)Migrations complete!$(NC)"

db-migrate-down: ## Rollback last migration
	@echo "$(BLUE)Rolling back last migration...$(NC)"
	cd database && alembic downgrade -1
	@echo "$(GREEN)Rollback complete!$(NC)"

db-migration-create: ## Create new migration (usage: make db-migration-create MSG="add new column")
	@if [ -z "$(MSG)" ]; then \
		echo "$(RED)Error: Please specify MSG parameter$(NC)"; \
		echo "$(YELLOW)Usage: make db-migration-create MSG="add new column"$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Creating migration: $(MSG)$(NC)"
	cd database && alembic revision --autogenerate -m "$(MSG)"
	@echo "$(GREEN)Migration created!$(NC)"

# ============================================
# Redis Commands
# ============================================
redis-shell: ## Open Redis CLI
	@echo "$(BLUE)Opening Redis CLI...$(NC)"
	docker-compose exec redis redis-cli -a redis123

redis-flush: ## Flush all Redis data
	@echo "$(RED)WARNING: This will delete all Redis data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(BLUE)Flushing Redis...$(NC)"; \
		docker-compose exec redis redis-cli -a redis123 FLUSHALL; \
		echo "$(GREEN)Redis flushed!$(NC)"; \
	else \
		echo "$(YELLOW)Aborted.$(NC)"; \
	fi

# ============================================
# Development Commands
# ============================================
install: ## Install Python dependencies
	@echo "$(BLUE)Installing dependencies...$(NC)"
	pip install --upgrade pip
	pip install -r platform-bot/requirements.txt
	pip install -r factory-service/requirements.txt
	pip install -r notification-service/requirements.txt
	pip install -r billing-service/requirements.txt
	@echo "$(GREEN)Dependencies installed!$(NC)"

clean: ## Clean up Docker resources
	@echo "$(BLUE)Cleaning up...$(NC)"
	docker-compose down -v
	docker system prune -f
	docker volume prune -f
	@echo "$(GREEN)Cleanup complete!$(NC)"

ps: ## Show running containers
	docker-compose ps

# ============================================
# Testing & Linting
# ============================================
test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	pytest
	@echo "$(GREEN)Tests complete!$(NC)"

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	pytest tests/unit
	@echo "$(GREEN)Unit tests complete!$(NC)"

test-integration: ## Run integration tests only
	@echo "$(BLUE)Running integration tests...$(NC)"
	pytest tests/integration
	@echo "$(GREEN)Integration tests complete!$(NC)"

lint: ## Run code linting
	@echo "$(BLUE)Linting code...$(NC)"
	ruff check .
	black --check .
	isort --check-only .
	@echo "$(GREEN)Linting complete!$(NC)"

format: ## Format code with black and isort
	@echo "$(BLUE)Formatting code...$(NC)"
	black .
	isort .
	@echo "$(GREEN)Code formatted!$(NC)"

# ============================================
# Production Commands
# ============================================
prod-up: ## Start production services
	@echo "$(BLUE)Starting production services...$(NC)"
	docker-compose -f docker-compose.prod.yml up -d
	@echo "$(GREEN)Production services started!$(NC)"

prod-logs: ## Show production logs
	docker-compose -f docker-compose.prod.yml logs -f

prod-down: ## Stop production services
	docker-compose -f docker-compose.prod.yml down

# ============================================
# Utility Commands
# ============================================
env-setup: ## Copy .env.example to .env
	@if [ ! -f .env ]; then \
		echo "$(BLUE)Creating .env file...$(NC)"; \
		cp .env.example .env; \
		echo "$(GREEN).env file created!$(NC)"; \
		echo "$(YELLOW)Please edit .env with your values$(NC)"; \
	else \
		echo "$(YELLOW).env file already exists$(NC)"; \
	fi

check-env: ## Check if .env file exists
	@if [ -f .env ]; then \
		echo "$(GREEN).env file exists$(NC)"; \
	else \
		echo "$(RED).env file not found!$(NC)"; \
		echo "$(YELLOW)Run 'make env-setup' to create it$(NC)"; \
		exit 1; \
	fi

health: ## Check health of all services
	@echo "$(BLUE)Checking service health...$(NC)"
	@echo -n "Database: "; \
	if docker-compose exec -T database pg_isready -U postgres -d bot_saas > /dev/null 2>&1; then \
		echo "$(GREEN)Healthy$(NC)"; \
	else \
		echo "$(RED)Unhealthy$(NC)"; \
	fi
	@echo -n "Redis: "; \
	if docker-compose exec -T redis redis-cli -a redis123 ping > /dev/null 2>&1; then \
		echo "$(GREEN)Healthy$(NC)"; \
	else \
		echo "$(RED)Unhealthy$(NC)"; \
	fi

# ============================================
# Info Commands
# ============================================
info: ## Show project information
	@echo "$(BLUE)Telegram Bot SaaS$(NC)"
	@echo ""
	@echo "$(GREEN)Project Status:$(NC)"
	@echo "  Services: $$(docker-compose ps -q | wc -l) running"
	@echo ""
	@echo "$(GREEN)Available URLs:$(NC)"
	@echo "  PostgreSQL: localhost:5432"
	@echo "  Redis:      localhost:6379"
	@echo "  pgAdmin:    http://localhost:5050"
	@echo "  Redis Cmd:  http://localhost:8082"
	@echo ""
	@echo "$(GREEN)Useful Commands:$(NC)"
	@echo "  make logs          - View logs"
	@echo "  make db-shell      - Open database shell"
	@echo "  make db-backup     - Backup database"
	@echo "  make health        - Check service health"
