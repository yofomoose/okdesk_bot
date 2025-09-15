#!/bin/bash

# 🚀 Быстрое обновление Okdesk Bot на сервере
# Использование: ./server-update.sh [rebuild]

set -e

echo "🚀 Быстрое обновление Okdesk Bot на сервере"
echo "==========================================="

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
RESET='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] $1${RESET}"
}

error() {
    echo -e "${RED}[ERROR] $1${RESET}"
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${RESET}"
}

# Проверка зависимостей
check_deps() {
    log "Проверка зависимостей..."
    command -v docker >/dev/null 2>&1 || { error "Docker не установлен"; exit 1; }
    command -v docker-compose >/dev/null 2>&1 || { error "Docker Compose не установлен"; exit 1; }
    log "✅ Зависимости OK"
}

# Резервное копирование
backup() {
    if [ -f "./data/okdesk_bot.db" ]; then
        log "Создание резервной копии..."
        cp ./data/okdesk_bot.db "./data/backup_$(date +%Y%m%d_%H%M%S).db"
        log "✅ Резервная копия создана"
    fi
}

# Обновление кода
update_code() {
    log "Обновление кода из Git..."
    git pull origin master
    log "✅ Код обновлен"
}

# Пересборка
rebuild() {
    local no_cache=$1
    log "Остановка контейнеров..."
    docker-compose down

    if [ "$no_cache" = "true" ]; then
        log "Полная пересборка (без кэша)..."
        docker-compose build --no-cache
    else
        log "Быстрая пересборка (с кэшем)..."
        docker-compose build
    fi
}

# Запуск
start() {
    log "Запуск сервисов..."
    docker-compose up -d
    sleep 5
}

# Проверка
check() {
    log "Проверка работоспособности..."

    if docker-compose ps | grep -q "Up"; then
        log "✅ Контейнеры запущены"

        if curl -s http://localhost:8000/ >/dev/null 2>&1; then
            log "✅ Webhook доступен"
        else
            warning "⚠️ Webhook недоступен"
        fi
    else
        error "❌ Контейнеры не запущены"
        exit 1
    fi
}

# Основная функция
main() {
    local rebuild=$1

    check_deps
    backup
    update_code
    rebuild "$rebuild"
    start
    check

    echo ""
    log "🎉 Обновление завершено успешно!"
    echo ""
    echo "📊 Статус: docker-compose ps"
    echo "📋 Логи: docker-compose logs --tail=20"
    echo "🛑 Остановка: docker-compose down"
}

# Обработка аргументов
case "$1" in
    "rebuild"|"-r"|"--rebuild")
        main "true"
        ;;
    "help"|"-h"|"--help")
        echo "Быстрое обновление Okdesk Bot"
        echo ""
        echo "Использование: $0 [rebuild]"
        echo ""
        echo "rebuild    - полная пересборка без кэша"
        echo ""
        echo "Примеры:"
        echo "  $0          # быстрая пересборка с кэшем"
        echo "  $0 rebuild  # полная пересборка"
        ;;
    *)
        main "false"
        ;;
esac