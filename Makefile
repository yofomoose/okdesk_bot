# Makefile для управления Okdesk Bot проектом
# Использование: make <команда>

.PHONY: help update deploy test logs status clean restart backup restore

# Переменные
COMPOSE_FILE = docker-compose.traefik.yml
PROJECT_NAME = okdesk_bot
BACKUP_DIR = ./backups
LOG_LINES = 100

# Цвета для вывода
RED = \033[31m
GREEN = \033[32m
YELLOW = \033[33m
BLUE = \033[34m
BOLD = \033[1m
RESET = \033[0m

help: ## Показать справку по командам
	@echo "$(BOLD)$(BLUE)🤖 Okdesk Bot - Управление проектом$(RESET)"
	@echo ""
	@echo "$(BOLD)Основные команды:$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BOLD)PostgreSQL команды:$(RESET)"
	@grep -E '^(db-|backup|restore):.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(BLUE)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Примеры использования:$(RESET)"
	@echo "  make update        # Обновить код и перезапустить"
	@echo "  make logs          # Посмотреть логи"
	@echo "  make db-status     # Проверить PostgreSQL"
	@echo "  make backup        # Создать бэкап БД"
	@echo "  make test          # Запустить тесты"

update: ## Полное обновление проекта (git pull + rebuild + restart)
	@echo "$(BOLD)$(BLUE)🔄 Начинаем полное обновление проекта...$(RESET)"
	@echo "$(YELLOW)📥 Получаем обновления из Git...$(RESET)"
	git pull origin master
	@echo "$(YELLOW)🛑 Останавливаем контейнеры...$(RESET)"
	docker-compose -f $(COMPOSE_FILE) down
	@echo "$(YELLOW)🔨 Пересобираем образы...$(RESET)"
	docker-compose -f $(COMPOSE_FILE) build --no-cache
	@echo "$(YELLOW)🚀 Запускаем обновленные контейнеры...$(RESET)"
	docker-compose -f $(COMPOSE_FILE) up -d
	@echo "$(GREEN)✅ Обновление завершено!$(RESET)"
	@make status

deploy: ## Быстрое развертывание без пересборки
	@echo "$(BOLD)$(BLUE)🚀 Быстрое развертывание...$(RESET)"
	docker-compose -f $(COMPOSE_FILE) down
	docker-compose -f $(COMPOSE_FILE) up -d
	@make status

restart: ## Перезапуск контейнеров
	@echo "$(BOLD)$(BLUE)🔄 Перезапуск контейнеров...$(RESET)"
	docker-compose -f $(COMPOSE_FILE) restart
	@make status

status: ## Проверить статус контейнеров и сервисов
	@echo "$(BOLD)$(BLUE)📊 Статус проекта$(RESET)"
	@echo ""
	@echo "$(BOLD)🐳 Статус контейнеров:$(RESET)"
	docker-compose -f $(COMPOSE_FILE) ps
	@echo ""
	@echo "$(BOLD)💾 Использование диска:$(RESET)"
	@docker system df
	@echo ""
	@echo "$(BOLD)🌐 Проверка webhook:$(RESET)"
	@curl -s -X GET https://yapomogu55.okdesk.ru:3000/health || echo "$(RED)❌ Webhook недоступен$(RESET)"
	@echo ""
	@echo "$(BOLD)📱 Telegram Bot API:$(RESET)"
	@curl -s "https://api.telegram.org/bot$$(grep BOT_TOKEN .env | cut -d'=' -f2)/getMe" | jq -r '.result.username' 2>/dev/null || echo "$(RED)❌ Bot API недоступен$(RESET)"

logs: ## Показать логи всех сервисов
	@echo "$(BOLD)$(BLUE)📋 Логи сервисов (последние $(LOG_LINES) строк)$(RESET)"
	docker-compose -f $(COMPOSE_FILE) logs --tail=$(LOG_LINES)

logs-live: ## Показать логи в реальном времени
	@echo "$(BOLD)$(BLUE)📋 Логи в реальном времени (Ctrl+C для выхода)$(RESET)"
	docker-compose -f $(COMPOSE_FILE) logs -f

logs-bot: ## Показать только логи бота
	@echo "$(BOLD)$(BLUE)🤖 Логи Telegram бота$(RESET)"
	docker logs $(PROJECT_NAME)_okdesk_bot_1 --tail=$(LOG_LINES)

logs-webhook: ## Показать только логи webhook сервера
	@echo "$(BOLD)$(BLUE)🌐 Логи Webhook сервера$(RESET)"
	docker logs $(PROJECT_NAME)_okdesk_webhook_1 --tail=$(LOG_LINES)

logs-errors: ## Показать только ошибки
	@echo "$(BOLD)$(RED)🚨 Ошибки в логах$(RESET)"
	docker-compose -f $(COMPOSE_FILE) logs | grep -i error || echo "$(GREEN)✅ Ошибок не найдено$(RESET)"

test: ## Запустить тесты и диагностику
	@echo "$(BOLD)$(BLUE)🧪 Запуск тестов и диагностики...$(RESET)"
	@echo ""
	@echo "$(BOLD)1. 🌐 Тест webhook:$(RESET)"
	@curl -X POST https://yapomogu55.okdesk.ru:3000/okdesk-webhook \
		-H "Content-Type: application/json" \
		-d '{"test": "connection", "timestamp": "'$$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' \
		-w "\nStatus: %{http_code}\n" || echo "$(RED)❌ Webhook тест провален$(RESET)"
	@echo ""
	@echo "$(BOLD)2. 🗄️ Тест базы данных:$(RESET)"
	@docker exec $(PROJECT_NAME)_postgres_1 psql -U okdesk_user -d okdesk_bot -c "SELECT COUNT(*) as users_count FROM users;" 2>/dev/null || echo "$(RED)❌ База данных недоступна$(RESET)"
	@echo ""
	@echo "$(BOLD)3. 🔗 Тест Okdesk API:$(RESET)"
	@curl -s "https://yapomogu55.okdesk.ru/api/v1/issues?limit=1&api_token=$$(grep OKDESK_API_TOKEN .env | cut -d'=' -f2)" \
		| jq -r 'if type == "array" then "✅ API работает" else "❌ API ошибка" end' 2>/dev/null || echo "$(RED)❌ Okdesk API недоступен$(RESET)"

test-comment: ## Тест создания комментария
	@echo "$(BOLD)$(BLUE)💬 Тест создания комментария...$(RESET)"
	@issue_id=$$(curl -s "https://yapomogu55.okdesk.ru/api/v1/issues?limit=1&api_token=$$(grep OKDESK_API_TOKEN .env | cut -d'=' -f2)" | jq -r '.[0].id' 2>/dev/null); \
	if [ "$$issue_id" != "null" ] && [ "$$issue_id" != "" ]; then \
		curl -X POST "https://yapomogu55.okdesk.ru/api/v1/issues/$$issue_id/comments?api_token=$$(grep OKDESK_API_TOKEN .env | cut -d'=' -f2)" \
			-H "Content-Type: application/json" \
			-d '{"content": "**От пользователя: Тестовый пользователь**\n\nТест создания комментария через Makefile", "public": true, "author_id": 1}' \
			-w "\nStatus: %{http_code}\n"; \
	else \
		echo "$(RED)❌ Не найдено заявок для тестирования$(RESET)"; \
	fi

backup: ## Создать резервную копию базы данных PostgreSQL
	@echo "$(BOLD)$(BLUE)💾 Создание резервной копии PostgreSQL...$(RESET)"
	@mkdir -p $(BACKUP_DIR)
	@timestamp=$$(date +%Y%m%d_%H%M%S); \
	docker exec $(PROJECT_NAME)_postgres_1 pg_dump -U okdesk_user -d okdesk_bot > $(BACKUP_DIR)/okdesk_bot_$$timestamp.sql && \
	echo "$(GREEN)✅ Резервная копия создана: $(BACKUP_DIR)/okdesk_bot_$$timestamp.sql$(RESET)"

restore: ## Восстановить базу данных PostgreSQL из резервной копии
	@echo "$(BOLD)$(YELLOW)⚠️  Восстановление базы данных PostgreSQL$(RESET)"
	@echo "Доступные резервные копии:"
	@ls -la $(BACKUP_DIR)/*.sql 2>/dev/null || echo "$(RED)❌ Резервные копии не найдены$(RESET)"
	@echo ""
	@echo "$(YELLOW)Для восстановления выполните:$(RESET)"
	@echo "cat $(BACKUP_DIR)/<файл_копии.sql> | docker exec -i $(PROJECT_NAME)_postgres_1 psql -U okdesk_user -d okdesk_bot"
	@echo "make restart"

clean: ## Очистка системы (удаление неиспользуемых образов и томов)
	@echo "$(BOLD)$(YELLOW)🧹 Очистка системы...$(RESET)"
	docker system prune -f
	docker volume prune -f
	@echo "$(GREEN)✅ Очистка завершена$(RESET)"

stop: ## Остановить все контейнеры
	@echo "$(BOLD)$(YELLOW)🛑 Останавливаем все контейнеры...$(RESET)"
	docker-compose -f $(COMPOSE_FILE) down --remove-orphans

start: ## Запустить все контейнеры
	@echo "$(BOLD)$(GREEN)🚀 Запускаем все контейнеры...$(RESET)"
	docker-compose -f $(COMPOSE_FILE) up -d

db-users: ## Показать пользователей из базы данных
	@echo "$(BOLD)$(BLUE)👥 Пользователи в базе данных:$(RESET)"
	@docker exec $(PROJECT_NAME)_okdesk_bot_1 sqlite3 /app/data/okdesk_bot.db \
		"SELECT telegram_id, username, full_name, phone, is_registered, created_at FROM users ORDER BY created_at DESC;" \
		2>/dev/null || echo "$(RED)❌ Ошибка доступа к базе данных$(RESET)"

db-issues: ## Показать заявки из базы данных
	@echo "$(BOLD)$(BLUE)📋 Заявки в базе данных:$(RESET)"
	@docker exec $(PROJECT_NAME)_okdesk_bot_1 sqlite3 /app/data/okdesk_bot.db \
		"SELECT okdesk_issue_id, title, status, created_at FROM issues ORDER BY created_at DESC LIMIT 10;" \
		2>/dev/null || echo "$(RED)❌ Ошибка доступа к базе данных$(RESET)"

db-comments: ## Показать комментарии из базы данных
	@echo "$(BOLD)$(BLUE)💬 Комментарии в базе данных:$(RESET)"
	@docker exec $(PROJECT_NAME)_okdesk_bot_1 sqlite3 /app/data/okdesk_bot.db \
		"SELECT issue_id, content, is_from_okdesk, created_at FROM comments ORDER BY created_at DESC LIMIT 10;" \
		2>/dev/null || echo "$(RED)❌ Ошибка доступа к базе данных$(RESET)"

monitor: ## Мониторинг системы в реальном времени
	@echo "$(BOLD)$(BLUE)📊 Мониторинг системы (обновление каждые 5 сек, Ctrl+C для выхода)$(RESET)"
	@while true; do \
		clear; \
		echo "$(BOLD)$(BLUE)🤖 Okdesk Bot - Мониторинг $(RESET) $$(date)"; \
		echo ""; \
		echo "$(BOLD)🐳 Контейнеры:$(RESET)"; \
		docker-compose -f $(COMPOSE_FILE) ps; \
		echo ""; \
		echo "$(BOLD)📈 Ресурсы:$(RESET)"; \
		docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"; \
		echo ""; \
		echo "$(BOLD)🌐 Последние запросы к webhook:$(RESET)"; \
		docker logs $(PROJECT_NAME)_okdesk_webhook_1 --tail=3 2>/dev/null | grep -E "(INFO|POST|GET)" || echo "Нет данных"; \
		sleep 5; \
	done

git-commit: ## Коммит и отправка изменений в Git
	@echo "$(BOLD)$(BLUE)📤 Отправка изменений в Git...$(RESET)"
	git add .
	@read -p "Введите сообщение коммита: " commit_msg; \
	git commit -m "$$commit_msg" && \
	git push origin master && \
	echo "$(GREEN)✅ Изменения отправлены в Git$(RESET)"

full-cycle: ## Полный цикл обновления (git commit + push + deploy)
	@echo "$(BOLD)$(BLUE)🔄 Полный цикл обновления...$(RESET)"
	@make git-commit
	@make update
	@make test
	@echo "$(GREEN)✅ Полный цикл завершен!$(RESET)"

# Docker оптимизация
build-fast: ## Быстрая сборка с кэшированием
	@echo "$(BOLD)$(BLUE)⚡ Быстрая сборка с кэшированием...$(RESET)"
	docker-compose -f $(COMPOSE_FILE) build

build-no-cache: ## Полная пересборка без кэша
	@echo "$(BOLD)$(BLUE)🔄 Полная пересборка без кэша...$(RESET)"
	docker-compose -f $(COMPOSE_FILE) build --no-cache

build-parallel: ## Параллельная сборка
	@echo "$(BOLD)$(BLUE)🔄 Параллельная сборка...$(RESET)"
	DOCKER_BUILDKIT=1 docker-compose -f $(COMPOSE_FILE) build --parallel

rebuild-bot: ## Пересборка только бота
	@echo "$(BOLD)$(BLUE)🤖 Пересборка только бота...$(RESET)"
	docker-compose -f $(COMPOSE_FILE) build --no-cache bot

rebuild-webhook: ## Пересборка только webhook
	@echo "$(BOLD)$(BLUE)🌐 Пересборка только webhook...$(RESET)"
	docker-compose -f $(COMPOSE_FILE) build --no-cache webhook

clean-images: ## Очистка неиспользуемых образов
	@echo "$(BOLD)$(BLUE)🧹 Очистка неиспользуемых образов...$(RESET)"
	docker image prune -f

clean-build-cache: ## Очистка кэша сборки
	@echo "$(BOLD)$(BLUE)🧹 Очистка кэша сборки...$(RESET)"
	docker builder prune -f

optimize: ## Полная оптимизация Docker
	@echo "$(BOLD)$(BLUE)🔧 Полная оптимизация Docker...$(RESET)"
	@echo "$(YELLOW)Остановка контейнеров...$(RESET)"
	docker-compose -f $(COMPOSE_FILE) down
	@echo "$(YELLOW)Очистка неиспользуемых ресурсов...$(RESET)"
	docker system prune -f
	@echo "$(YELLOW)Очистка кэша сборки...$(RESET)"
	docker builder prune -f
	@echo "$(GREEN)✅ Оптимизация завершена!$(RESET)"

# PostgreSQL команды
db-connect: ## Подключиться к PostgreSQL базе данных
	@echo "$(BOLD)$(BLUE)🗄️ Подключение к PostgreSQL...$(RESET)"
	docker exec -it $(PROJECT_NAME)_postgres_1 psql -U okdesk_user -d okdesk_bot

db-shell: ## Открыть PostgreSQL shell
	@echo "$(BOLD)$(BLUE)🐚 PostgreSQL Shell...$(RESET)"
	docker exec -it $(PROJECT_NAME)_postgres_1 bash -c "psql -U okdesk_user -d okdesk_bot"

db-logs: ## Показать логи PostgreSQL
	@echo "$(BOLD)$(BLUE)📋 Логи PostgreSQL$(RESET)"
	docker logs $(PROJECT_NAME)_postgres_1 --tail=$(LOG_LINES)

db-status: ## Проверить статус PostgreSQL
	@echo "$(BOLD)$(BLUE)📊 Статус PostgreSQL$(RESET)"
	@docker exec $(PROJECT_NAME)_postgres_1 pg_isready -U okdesk_user -d okdesk_bot && echo "$(GREEN)✅ PostgreSQL готов$(RESET)" || echo "$(RED)❌ PostgreSQL недоступен$(RESET)"

db-migrate: ## Запустить миграцию из SQLite в PostgreSQL
	@echo "$(BOLD)$(BLUE)🔄 Миграция данных из SQLite в PostgreSQL...$(RESET)"
	@echo "$(YELLOW)Убедитесь что файл okdesk_bot.db находится в корне проекта$(RESET)"
	@docker run --rm -v $$(pwd):/app -w /app --network $(PROJECT_NAME)_default \
		python:3.11-slim bash -c "pip install -r requirements.txt && python migrate_to_postgres.py"

db-reset: ## Сбросить базу данных PostgreSQL (ОСТОРОЖНО!)
	@echo "$(BOLD)$(RED)⚠️  ВНИМАНИЕ: Это удалит все данные!$(RESET)"
	@echo "$(YELLOW)Для продолжения выполните: make db-reset-confirm$(RESET)"

db-reset-confirm: ## Подтвердить сброс базы данных PostgreSQL
	@echo "$(BOLD)$(RED)🗑️ Сброс базы данных PostgreSQL...$(RESET)"
	docker exec $(PROJECT_NAME)_postgres_1 psql -U okdesk_user -d okdesk_bot -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO okdesk_user;"
	@echo "$(YELLOW)Перезапустите контейнеры для пересоздания таблиц$(RESET)"

# Команда по умолчанию
all: help
