#!/bin/bash

# 🚀 Быстрое исправление проблемы readonly базы данных
# Использование: ./fix-db.sh

echo "🚀 Исправление проблемы readonly базы данных"
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

# Исправление прав доступа
fix_permissions() {
    log "Исправление прав доступа..."

    # Исправление прав на файл
    if [ -f "./data/okdesk_bot.db" ]; then
        chmod 666 ./data/okdesk_bot.db
        log "✅ Права файла исправлены"
    else
        warning "⚠️ Файл базы данных не найден"
    fi

    # Исправление прав на директорию
    if [ -d "./data" ]; then
        chmod 755 ./data
        log "✅ Права директории исправлены"
    else
        mkdir -p ./data
        chmod 755 ./data
        log "✅ Директория создана и права исправлены"
    fi
}

# Исправление через Docker
fix_docker_permissions() {
    log "Исправление прав через Docker..."

    # Исправление прав внутри контейнера
    docker-compose exec bot chmod 666 /app/data/okdesk_bot.db 2>/dev/null || warning "Не удалось исправить права через контейнер"
    docker-compose exec bot chmod 755 /app/data 2>/dev/null || warning "Не удалось исправить права директории через контейнер"
}

# Перезапуск сервисов
restart_services() {
    log "Перезапуск сервисов..."

    docker-compose down
    sleep 2
    docker-compose up -d
    sleep 5

    if docker-compose ps | grep -q "Up"; then
        log "✅ Сервисы перезапущены успешно"
    else
        error "❌ Ошибка перезапуска сервисов"
    fi
}

# Проверка исправления
check_fix() {
    log "Проверка исправления..."

    # Проверка прав
    if [ -f "./data/okdesk_bot.db" ] && [ -w "./data/okdesk_bot.db" ]; then
        log "✅ Права доступа исправлены"
    else
        error "❌ Права доступа не исправлены"
        return 1
    fi

    # Проверка контейнеров
    if docker-compose ps | grep -q "Up"; then
        log "✅ Контейнеры работают"
    else
        error "❌ Контейнеры не работают"
        return 1
    fi

    # Проверка логов на ошибки
    if docker-compose logs bot --tail=10 | grep -q "readonly database"; then
        error "❌ Ошибка readonly database все еще присутствует"
        return 1
    else
        log "✅ Ошибок readonly database не найдено в логах"
    fi
}

# Основная функция
main() {
    echo ""

    # Шаг 1: Исправление прав
    fix_permissions
    echo ""

    # Шаг 2: Исправление через Docker (если контейнеры запущены)
    if docker-compose ps | grep -q "Up"; then
        fix_docker_permissions
        echo ""
    fi

    # Шаг 3: Перезапуск
    restart_services
    echo ""

    # Шаг 4: Проверка
    if check_fix; then
        echo ""
        log "🎉 Проблема исправлена успешно!"
        echo ""
        echo "📋 Следующие шаги:"
        echo "1. Проверьте логи: docker-compose logs bot --tail=10"
        echo "2. Протестируйте бота в Telegram"
        echo "3. Если проблема вернулась, проверьте: ./diagnose-db.sh"
    else
        echo ""
        error "❌ Автоматическое исправление не удалось"
        echo ""
        echo "🔧 Ручное исправление:"
        echo "1. Проверьте логи: docker-compose logs"
        echo "2. Подробная диагностика: ./diagnose-db.sh"
        echo "3. Пересоздайте базу: rm ./data/okdesk_bot.db && docker-compose restart"
    fi

    echo ""
    log "Исправление завершено"
}

# Запуск
main "$@"