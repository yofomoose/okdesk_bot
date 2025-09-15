#!/bin/bash

# 🔍 Диагностика проблемы с readonly базой данных SQLite
# Использование: ./diagnose-db.sh

echo "🔍 Диагностика проблемы с readonly базой данных"
echo "=============================================="

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Проверка существования файла базы данных
check_db_file() {
    log "Проверка файла базы данных..."

    if [ -f "./data/okdesk_bot.db" ]; then
        log "✅ Файл базы данных существует"
        ls -la ./data/okdesk_bot.db
    else
        warning "⚠️ Файл базы данных не найден"
        return 1
    fi
}

# Проверка прав доступа
check_permissions() {
    log "Проверка прав доступа..."

    if [ -f "./data/okdesk_bot.db" ]; then
        PERMS=$(stat -c "%a %U:%G" ./data/okdesk_bot.db 2>/dev/null || echo "stat не поддерживается")

        # Проверка прав на запись
        if [ -w "./data/okdesk_bot.db" ]; then
            log "✅ Права на запись: OK"
        else
            error "❌ Нет прав на запись в файл базы данных"
            echo "Текущие права: $PERMS"
            return 1
        fi

        # Проверка прав на директорию
        if [ -w "./data" ]; then
            log "✅ Права на директорию: OK"
        else
            error "❌ Нет прав на запись в директорию ./data"
            ls -ld ./data
            return 1
        fi
    fi
}

# Проверка Docker контейнеров
check_docker() {
    log "Проверка Docker контейнеров..."

    if command -v docker &> /dev/null; then
        # Проверка запущенных контейнеров
        RUNNING=$(docker ps --filter "name=okdesk" --format "{{.Names}}" | wc -l)
        if [ "$RUNNING" -gt 0 ]; then
            log "✅ Docker контейнеры запущены: $RUNNING"
            docker ps --filter "name=okdesk" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        else
            warning "⚠️ Docker контейнеры не запущены"
        fi

        # Проверка volumes
        log "Проверка Docker volumes..."
        docker volume ls | grep -E "(okdesk|data)" || warning "Не найдены volumes связанные с проектом"
    else
        warning "⚠️ Docker не установлен"
    fi
}

# Проверка SQLite файла
check_sqlite() {
    log "Проверка SQLite файла..."

    if [ -f "./data/okdesk_bot.db" ]; then
        # Проверка размера файла
        SIZE=$(stat -c%s "./data/okdesk_bot.db" 2>/dev/null || echo "неизвестно")
        log "Размер файла: ${SIZE} байт"

        # Попытка выполнить простой запрос
        if command -v sqlite3 &> /dev/null; then
            log "Тестирование SQLite подключения..."
            if sqlite3 ./data/okdesk_bot.db "SELECT COUNT(*) FROM sqlite_master;" >/dev/null 2>&1; then
                log "✅ SQLite подключение: OK"

                # Показать таблицы
                TABLES=$(sqlite3 ./data/okdesk_bot.db ".tables")
                log "Найденные таблицы: $TABLES"

                # Показать количество записей
                for table in $TABLES; do
                    COUNT=$(sqlite3 ./data/okdesk_bot.db "SELECT COUNT(*) FROM $table;")
                    info "Таблица $table: $COUNT записей"
                done
            else
                error "❌ Ошибка подключения к SQLite"
                return 1
            fi
        else
            warning "⚠️ sqlite3 не установлен, пропускаем тест"
        fi
    fi
}

# Исправление проблем
fix_issues() {
    log "Исправление найденных проблем..."

    # Исправление прав доступа
    if [ -f "./data/okdesk_bot.db" ]; then
        log "Исправление прав доступа к файлу базы данных..."
        chmod 666 ./data/okdesk_bot.db
        log "✅ Права файла исправлены"

        log "Исправление прав доступа к директории..."
        chmod 755 ./data
        log "✅ Права директории исправлены"
    fi

    # Создание директории если не существует
    if [ ! -d "./data" ]; then
        log "Создание директории ./data..."
        mkdir -p ./data
        chmod 755 ./data
        log "✅ Директория создана"
    fi

    # Создание новой базы данных если файл поврежден
    if [ ! -f "./data/okdesk_bot.db" ] || [ ! -s "./data/okdesk_bot.db" ]; then
        log "Создание новой базы данных..."
        if command -v sqlite3 &> /dev/null; then
            sqlite3 ./data/okdesk_bot.db ".read schema.sql" 2>/dev/null || {
                # Если нет schema.sql, создаем минимальную структуру
                sqlite3 ./data/okdesk_bot.db << 'EOF'
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    telegram_id INTEGER UNIQUE,
    username TEXT,
    user_type TEXT,
    full_name TEXT,
    phone TEXT,
    contact_auth_code TEXT,
    okdesk_contact_id INTEGER,
    inn_company TEXT,
    company_id INTEGER,
    company_name TEXT,
    is_registered BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY,
    telegram_user_id INTEGER,
    okdesk_issue_id INTEGER,
    title TEXT,
    description TEXT,
    status TEXT,
    priority TEXT,
    okdesk_url TEXT,
    issue_number TEXT,
    rating INTEGER,
    rating_comment TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY,
    issue_id INTEGER,
    okdesk_comment_id INTEGER,
    telegram_user_id INTEGER,
    content TEXT,
    is_from_okdesk BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
EOF
            }
            chmod 666 ./data/okdesk_bot.db
            log "✅ Новая база данных создана"
        fi
    fi
}

# Перезапуск сервисов
restart_services() {
    log "Перезапуск Docker сервисов..."

    if command -v docker-compose &> /dev/null; then
        docker-compose down
        sleep 2
        docker-compose up -d
        sleep 5

        if docker-compose ps | grep -q "Up"; then
            log "✅ Сервисы успешно перезапущены"
        else
            error "❌ Ошибка перезапуска сервисов"
        fi
    else
        warning "⚠️ docker-compose не найден"
    fi
}

# Основная функция
main() {
    echo ""
    check_db_file
    echo ""
    check_permissions
    echo ""
    check_docker
    echo ""
    check_sqlite
    echo ""

    # Предложение исправлений
    echo "🔧 Возможные исправления:"
    echo "1. Исправить права доступа"
    echo "2. Пересоздать базу данных"
    echo "3. Перезапустить сервисы"
    echo ""

    read -p "Хотите автоматически исправить проблемы? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        fix_issues
        echo ""
        read -p "Перезапустить сервисы? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            restart_services
        fi
    fi

    echo ""
    log "Диагностика завершена"
}

# Запуск диагностики
main "$@"