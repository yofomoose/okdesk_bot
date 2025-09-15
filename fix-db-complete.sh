#!/bin/bash

# 🚀 Исправление проблемы readonly базы данных - ПОЛНАЯ ВЕРСИЯ
# Выполните на сервере: ./fix-db-complete.sh

echo "🚀 ПОЛНОЕ ИСПРАВЛЕНИЕ ПРОБЛЕМЫ READONLY БАЗЫ ДАННЫХ"
echo "=================================================="

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
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

info() {
    echo -e "${BLUE}[INFO] $1${RESET}"
}

# Шаг 1: Проверка статуса контейнеров
check_containers() {
    log "Шаг 1: Проверка статуса контейнеров"
    echo "Текущий статус:"
    docker-compose ps
    echo ""
}

# Шаг 2: Запуск контейнеров если не запущены
start_containers() {
    log "Шаг 2: Запуск контейнеров"

    RUNNING=$(docker-compose ps | grep "Up" | wc -l)
    if [ "$RUNNING" -eq 0 ]; then
        log "Контейнеры не запущены, запускаю..."
        docker-compose up -d

        # Ждем запуска
        sleep 5

        # Проверяем статус
        RUNNING_AFTER=$(docker-compose ps | grep "Up" | wc -l)
        if [ "$RUNNING_AFTER" -gt 0 ]; then
            log "✅ Контейнеры успешно запущены ($RUNNING_AFTER)"
        else
            error "❌ Не удалось запустить контейнеры"
            exit 1
        fi
    else
        log "✅ Контейнеры уже запущены ($RUNNING)"
    fi
    echo ""
}

# Шаг 3: Исправление прав через Docker
fix_docker_permissions() {
    log "Шаг 3: Исправление прав через Docker"

    # Исправление прав на файл базы данных
    if docker-compose exec -T bot chmod 666 /app/data/okdesk_bot.db 2>/dev/null; then
        log "✅ Права на файл базы данных исправлены (bot)"
    else
        warning "⚠️ Не удалось исправить права через контейнер bot"
    fi

    if docker-compose exec -T webhook chmod 666 /app/data/okdesk_bot.db 2>/dev/null; then
        log "✅ Права на файл базы данных исправлены (webhook)"
    else
        warning "⚠️ Не удалось исправить права через контейнер webhook"
    fi

    # Исправление прав на директорию
    if docker-compose exec -T bot chmod 755 /app/data 2>/dev/null; then
        log "✅ Права на директорию исправлены"
    else
        warning "⚠️ Не удалось исправить права на директорию"
    fi
    echo ""
}

# Шаг 4: Исправление прав на хосте
fix_host_permissions() {
    log "Шаг 4: Исправление прав на хосте"

    # Проверка существования файла
    if [ -f "./data/okdesk_bot.db" ]; then
        log "Файл базы данных найден"

        # Текущие права
        ls -la ./data/okdesk_bot.db

        # Исправление прав
        if chmod 666 ./data/okdesk_bot.db; then
            log "✅ Права на файл исправлены"
        else
            error "❌ Не удалось исправить права на файл"
        fi
    else
        warning "⚠️ Файл базы данных не найден"
    fi

    # Исправление прав на директорию
    if [ -d "./data" ]; then
        if chmod 755 ./data; then
            log "✅ Права на директорию исправлены"
        else
            error "❌ Не удалось исправить права на директорию"
        fi
    else
        warning "⚠️ Директория ./data не найдена"
    fi
    echo ""
}

# Шаг 5: Перезапуск сервисов
restart_services() {
    log "Шаг 5: Перезапуск сервисов"

    docker-compose down
    sleep 2
    docker-compose up -d
    sleep 5

    # Проверка статуса
    RUNNING=$(docker-compose ps | grep "Up" | wc -l)
    if [ "$RUNNING" -gt 0 ]; then
        log "✅ Сервисы успешно перезапущены ($RUNNING)"
    else
        error "❌ Ошибка перезапуска сервисов"
        exit 1
    fi
    echo ""
}

# Шаг 6: Финальная проверка
final_check() {
    log "Шаг 6: Финальная проверка"

    # Проверка контейнеров
    echo "Статус контейнеров:"
    docker-compose ps
    echo ""

    # Проверка логов на ошибки
    echo "Последние логи бота:"
    docker-compose logs bot --tail=5
    echo ""

    # Проверка на ошибки readonly
    if docker-compose logs bot --tail=10 | grep -q "readonly database"; then
        error "❌ Ошибка readonly database все еще присутствует"
        echo ""
        echo "🔧 Дополнительные действия:"
        echo "1. Проверьте дисковое пространство: df -h"
        echo "2. Проверьте файловую систему: mount | grep data"
        echo "3. Попробуйте пересоздать базу данных"
        return 1
    else
        log "✅ Ошибок readonly database не найдено"
    fi

    # Проверка прав доступа
    if [ -f "./data/okdesk_bot.db" ]; then
        PERMS=$(ls -l ./data/okdesk_bot.db | awk '{print $1}')
        if [[ $PERMS == *rw* ]]; then
            log "✅ Права доступа корректны"
        else
            warning "⚠️ Возможны проблемы с правами доступа"
        fi
    fi
}

# Основная функция
main() {
    echo "Начинаем исправление проблемы readonly базы данных..."
    echo ""

    check_containers
    start_containers
    fix_docker_permissions
    fix_host_permissions
    restart_services
    final_check

    echo ""
    log "🎉 ИСПРАВЛЕНИЕ ЗАВЕРШЕНО!"
    echo ""
    echo "📋 РЕЗУЛЬТАТЫ:"
    echo "• Контейнеры запущены и работают"
    echo "• Права доступа исправлены"
    echo "• База данных должна работать корректно"
    echo ""
    echo "📊 ПРОВЕРКА:"
    echo "• docker-compose logs bot --tail=10"
    echo "• docker-compose ps"
    echo ""
    echo "🔍 ЕСЛИ ПРОБЛЕМА СОХРАНИЛАСЬ:"
    echo "• ./diagnose-db.sh - подробная диагностика"
    echo "• rm ./data/okdesk_bot.db && docker-compose restart - пересоздать БД"
}

# Запуск
main "$@"