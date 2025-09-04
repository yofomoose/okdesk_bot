#!/bin/bash

# 🔧 Скрипт управления Okdesk Bot
# Автоматизация развертывания, диагностики и управления

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Переменные
PROJECT_DIR="/opt/okdesk_bot"
DOCKER_COMPOSE_FILE="docker-compose.traefik.yml"
BOT_CONTAINER="okdesk_bot_okdesk_bot_1"
WEBHOOK_CONTAINER="okdesk_bot_okdesk_webhook_1"

echo -e "${BLUE}🤖 Okdesk Bot Management Script${NC}"
echo -e "${CYAN}================================${NC}"

# Функция для логирования
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

# Проверка зависимостей
check_dependencies() {
    log "Проверка зависимостей..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker не установлен"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose не установлен"
        exit 1
    fi
    
    if ! command -v git &> /dev/null; then
        error "Git не установлен"
        exit 1
    fi
    
    log "✅ Все зависимости установлены"
}

# Обновление кода
update_code() {
    log "📥 Обновление кода из GitHub..."
    
    cd "$PROJECT_DIR"
    
    # Сохраняем текущие изменения
    if [ -n "$(git status --porcelain)" ]; then
        warning "Обнаружены локальные изменения. Сохраняем..."
        git stash push -m "Auto-stash before update $(date)"
    fi
    
    # Обновляем код
    git fetch origin
    git pull origin master
    
    log "✅ Код обновлен"
}

# Сборка контейнеров
build_containers() {
    log "🏗️ Сборка Docker контейнеров..."
    
    cd "$PROJECT_DIR"
    docker-compose -f "$DOCKER_COMPOSE_FILE" build --no-cache
    
    log "✅ Контейнеры собраны"
}

# Запуск контейнеров
start_containers() {
    log "🚀 Запуск контейнеров..."
    
    cd "$PROJECT_DIR"
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    
    log "✅ Контейнеры запущены"
}

# Остановка контейнеров
stop_containers() {
    log "⏹️ Остановка контейнеров..."
    
    cd "$PROJECT_DIR"
    docker-compose -f "$DOCKER_COMPOSE_FILE" down
    
    log "✅ Контейнеры остановлены"
}

# Перезапуск контейнеров
restart_containers() {
    log "🔄 Перезапуск контейнеров..."
    
    stop_containers
    start_containers
    
    log "✅ Контейнеры перезапущены"
}

# Полное обновление
full_update() {
    log "🚀 Выполняется полное обновление..."
    
    check_dependencies
    update_code
    stop_containers
    build_containers
    start_containers
    
    log "✅ Полное обновление завершено"
    
    # Показываем статус
    sleep 3
    show_status
}

# Показать статус
show_status() {
    log "📊 Статус контейнеров:"
    
    cd "$PROJECT_DIR"
    docker-compose -f "$DOCKER_COMPOSE_FILE" ps
    
    echo ""
    log "🔍 Проверка доступности сервисов:"
    
    # Проверка webhook
    echo -n "Webhook сервер: "
    if curl -s "https://yapomogu55.okdesk.ru:3000/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Доступен${NC}"
    else
        echo -e "${RED}❌ Недоступен${NC}"
    fi
    
    # Проверка бота
    echo -n "Telegram бот: "
    if docker logs "$BOT_CONTAINER" --tail 5 2>/dev/null | grep -q "Start polling"; then
        echo -e "${GREEN}✅ Работает${NC}"
    else
        echo -e "${RED}❌ Не работает${NC}"
    fi
}

# Показать логи
show_logs() {
    local service="$1"
    local lines="${2:-50}"
    
    cd "$PROJECT_DIR"
    
    if [ -z "$service" ]; then
        log "📋 Логи всех сервисов (последние $lines строк):"
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs --tail="$lines"
    else
        log "📋 Логи сервиса $service (последние $lines строк):"
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs --tail="$lines" "$service"
    fi
}

# Следить за логами в реальном времени
follow_logs() {
    local service="$1"
    
    cd "$PROJECT_DIR"
    
    if [ -z "$service" ]; then
        log "📋 Отслеживание логов всех сервисов..."
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f
    else
        log "📋 Отслеживание логов сервиса $service..."
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f "$service"
    fi
}

# Диагностика
diagnose() {
    log "🔍 Запуск диагностики..."
    
    echo ""
    echo -e "${PURPLE}=== СИСТЕМНАЯ ИНФОРМАЦИЯ ===${NC}"
    echo "Дата: $(date)"
    echo "Uptime: $(uptime)"
    echo "Место на диске:"
    df -h "$PROJECT_DIR"
    
    echo ""
    echo -e "${PURPLE}=== DOCKER ИНФОРМАЦИЯ ===${NC}"
    echo "Docker версия: $(docker --version)"
    echo "Docker Compose версия: $(docker-compose --version)"
    echo "Запущенные контейнеры:"
    docker ps --filter "name=okdesk_bot"
    
    echo ""
    echo -e "${PURPLE}=== СТАТУС СЕРВИСОВ ===${NC}"
    show_status
    
    echo ""
    echo -e "${PURPLE}=== ПРОВЕРКА ПОДКЛЮЧЕНИЙ ===${NC}"
    
    # Проверка подключения к Okdesk API
    echo -n "Okdesk API: "
    if curl -s "https://yapomogu55.okdesk.ru/api/v1/companies?api_token=4cf96e5bb33f06481e4aff5ff0a2aa740ce8490a" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Доступен${NC}"
    else
        echo -e "${RED}❌ Недоступен${NC}"
    fi
    
    # Проверка webhook
    echo -n "Webhook endpoint: "
    if curl -s "https://yapomogu55.okdesk.ru:3000/okdesk-webhook" -X POST -H "Content-Type: application/json" -d '{"test": true}' > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Доступен${NC}"
    else
        echo -e "${RED}❌ Недоступен${NC}"
    fi
    
    echo ""
    echo -e "${PURPLE}=== ОШИБКИ В ЛОГАХ ===${NC}"
    if docker logs "$BOT_CONTAINER" --tail 100 2>/dev/null | grep -i error; then
        warning "Обнаружены ошибки в логах бота"
    else
        log "Ошибок в логах бота не найдено"
    fi
    
    if docker logs "$WEBHOOK_CONTAINER" --tail 100 2>/dev/null | grep -i error; then
        warning "Обнаружены ошибки в логах webhook"
    else
        log "Ошибок в логах webhook не найдено"
    fi
    
    echo ""
    echo -e "${PURPLE}=== БАЗА ДАННЫХ ===${NC}"
    echo "Пользователи в базе:"
    docker exec "$BOT_CONTAINER" sqlite3 /app/data/okdesk_bot.db \
        "SELECT COUNT(*) as total_users, 
                SUM(CASE WHEN is_registered = 1 THEN 1 ELSE 0 END) as registered_users 
         FROM users;" 2>/dev/null || echo "Ошибка доступа к базе данных"
    
    echo "Заявки в базе:"
    docker exec "$BOT_CONTAINER" sqlite3 /app/data/okdesk_bot.db \
        "SELECT COUNT(*) as total_issues FROM issues;" 2>/dev/null || echo "Ошибка доступа к базе данных"
}

# Тест создания комментария
test_comment() {
    log "🧪 Тестирование создания комментария..."
    
    # Получаем ID первой заявки
    local issue_id=$(curl -s "https://yapomogu55.okdesk.ru/api/v1/issues?limit=1&api_token=4cf96e5bb33f06481e4aff5ff0a2aa740ce8490a" | \
                     python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0]['id'] if data else '')" 2>/dev/null)
    
    if [ -n "$issue_id" ]; then
        log "Создание тестового комментария к заявке #$issue_id..."
        
        curl -X POST "https://yapomogu55.okdesk.ru/api/v1/issues/$issue_id/comments?api_token=4cf96e5bb33f06481e4aff5ff0a2aa740ce8490a" \
             -H "Content-Type: application/json" \
             -d '{
                 "content": "**Тестовый комментарий от управляющего скрипта**\n\nВремя: '$(date)'",
                 "public": true,
                 "author_id": 1
             }'
        echo ""
        log "✅ Тестовый комментарий создан"
    else
        error "Не найдено заявок для тестирования"
    fi
}

# Резервное копирование базы данных
backup_database() {
    log "💾 Создание резервной копии базы данных..."
    
    local backup_dir="/opt/okdesk_bot/backups"
    local backup_file="$backup_dir/okdesk_bot_$(date +%Y%m%d_%H%M%S).db"
    
    mkdir -p "$backup_dir"
    
    docker cp "$BOT_CONTAINER:/app/data/okdesk_bot.db" "$backup_file"
    
    log "✅ Резервная копия сохранена: $backup_file"
}

# Очистка старых логов Docker
cleanup_logs() {
    log "🧹 Очистка логов Docker..."
    
    docker system prune -f
    
    log "✅ Логи очищены"
}

# Показать помощь
show_help() {
    echo -e "${CYAN}Использование: $0 [КОМАНДА]${NC}"
    echo ""
    echo -e "${YELLOW}ОСНОВНЫЕ КОМАНДЫ:${NC}"
    echo "  update      - Полное обновление (код + перезапуск)"
    echo "  start       - Запуск контейнеров"
    echo "  stop        - Остановка контейнеров"
    echo "  restart     - Перезапуск контейнеров"
    echo "  status      - Показать статус сервисов"
    echo ""
    echo -e "${YELLOW}ДИАГНОСТИКА:${NC}"
    echo "  diagnose    - Полная диагностика системы"
    echo "  logs [srv]  - Показать логи (all|okdesk_bot|okdesk_webhook)"
    echo "  follow [srv]- Следить за логами в реальном времени"
    echo "  test        - Тест создания комментария"
    echo ""
    echo -e "${YELLOW}ОБСЛУЖИВАНИЕ:${NC}"
    echo "  backup      - Резервная копия базы данных"
    echo "  cleanup     - Очистка логов Docker"
    echo "  build       - Пересборка контейнеров"
    echo ""
    echo -e "${YELLOW}ПРИМЕРЫ:${NC}"
    echo "  $0 update              # Полное обновление"
    echo "  $0 logs okdesk_bot     # Логи только бота"
    echo "  $0 follow okdesk_webhook # Следить за логами webhook"
    echo "  $0 diagnose            # Полная диагностика"
}

# Основная логика
case "${1:-help}" in
    "update")
        full_update
        ;;
    "start")
        start_containers
        ;;
    "stop")
        stop_containers
        ;;
    "restart")
        restart_containers
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs "$2" "$3"
        ;;
    "follow")
        follow_logs "$2"
        ;;
    "diagnose")
        diagnose
        ;;
    "test")
        test_comment
        ;;
    "backup")
        backup_database
        ;;
    "cleanup")
        cleanup_logs
        ;;
    "build")
        build_containers
        ;;
    "help"|*)
        show_help
        ;;
esac
