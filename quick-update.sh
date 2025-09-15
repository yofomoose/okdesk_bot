#!/bin/bash

# Скрипт быстрого обновления и пересборки Docker образов
# Использование: ./quick-update.sh [rebuild]

set -e

echo "🚀 Быстрое обновление Okdesk Bot"
echo "================================="

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
RESET='\033[0m'

# Функция логирования
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${RESET}"
}

error() {
    echo -e "${RED}[ERROR] $1${RESET}"
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${RESET}"
}

info() {
    echo -e "${BLUE}[INFO] $1${RESET}"
}

# Проверка наличия docker и docker-compose
check_dependencies() {
    if ! command -v docker &> /dev/null; then
        error "Docker не установлен!"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose не установлен!"
        exit 1
    fi

    log "✅ Зависимости проверены"
}

# Остановка контейнеров
stop_containers() {
    log "🛑 Остановка контейнеров..."
    docker-compose down || warning "Не удалось остановить контейнеры"
}

# Резервное копирование базы данных
backup_database() {
    if [ -f "./data/okdesk_bot.db" ]; then
        log "💾 Создание резервной копии базы данных..."
        cp ./data/okdesk_bot.db "./data/backup_$(date +%Y%m%d_%H%M%S).db"
        log "✅ Резервная копия создана"
    fi
}

# Сборка образов
build_images() {
    local rebuild=$1

    if [ "$rebuild" = "rebuild" ]; then
        log "🔄 Полная пересборка образов (без кэша)..."
        docker-compose build --no-cache
    else
        log "⚡ Быстрая сборка образов (с кэшем)..."
        docker-compose build
    fi
}

# Запуск контейнеров
start_containers() {
    log "🚀 Запуск контейнеров..."
    docker-compose up -d
}

# Проверка статуса
check_status() {
    log "📊 Проверка статуса..."
    sleep 5

    if docker-compose ps | grep -q "Up"; then
        log "✅ Контейнеры успешно запущены"

        # Проверка webhook
        if curl -s http://localhost:8000/ > /dev/null; then
            log "✅ Webhook сервер доступен"
        else
            warning "⚠️ Webhook сервер недоступен"
        fi
    else
        error "❌ Контейнеры не запущены"
        exit 1
    fi
}

# Показать логи
show_logs() {
    echo ""
    info "📋 Последние логи (для просмотра всех логов используйте: make logs)"
    docker-compose logs --tail=10
}

# Основная функция
main() {
    local rebuild=$1

    echo -e "${BOLD}${BLUE}Начинаем обновление...${RESET}"
    echo ""

    check_dependencies
    stop_containers
    backup_database
    build_images "$rebuild"
    start_containers
    check_status
    show_logs

    echo ""
    log "🎉 Обновление завершено успешно!"
    echo ""
    info "Команды для управления:"
    echo "  make logs        - посмотреть логи"
    echo "  make status      - проверить статус"
    echo "  make restart     - перезапустить"
    echo "  make update      - полное обновление"
}

# Обработка аргументов
case "$1" in
    "rebuild"|"-r"|"--rebuild")
        main "rebuild"
        ;;
    "help"|"-h"|"--help")
        echo "Использование: $0 [rebuild]"
        echo ""
        echo "rebuild    - полная пересборка без кэша"
        echo ""
        echo "Примеры:"
        echo "  $0          # быстрая сборка с кэшем"
        echo "  $0 rebuild  # полная пересборка"
        ;;
    *)
        main
        ;;
esac