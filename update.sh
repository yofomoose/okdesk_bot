#!/bin/bash

# Скрипт автоматического обновления Okdesk Bot на сервере

echo "🔄 ОБНОВЛЕНИЕ OKDESK BOT"
echo "======================="

# Проверяем наличие git репозитория
if [ ! -d ".git" ]; then
    echo "❌ Это не git репозиторий!"
    exit 1
fi

# Сохраняем текущую ветку
CURRENT_BRANCH=$(git branch --show-current)
echo "📍 Текущая ветка: $CURRENT_BRANCH"

# Проверяем подключение к GitHub
echo "🌐 Проверяем подключение к GitHub..."
git fetch origin

# Проверяем есть ли обновления
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/$CURRENT_BRANCH)

if [ $LOCAL = $REMOTE ]; then
    echo "✅ Код уже актуальный, обновления не требуются"
    exit 0
fi

echo "📥 Найдены обновления, начинаем процесс..."

# Создаем бэкап базы данных
if [ -f "data/okdesk_bot.db" ]; then
    BACKUP_NAME="data/backup_$(date +%Y%m%d_%H%M%S).db"
    cp data/okdesk_bot.db $BACKUP_NAME
    echo "💾 Создан бэкап базы данных: $BACKUP_NAME"
fi

# Останавливаем контейнеры
echo "🛑 Остановка контейнеров..."
docker-compose down

# Получаем обновления
echo "📥 Получение обновлений с GitHub..."
git pull origin $CURRENT_BRANCH

# Проверяем изменения в зависимостях
if git diff HEAD~1 HEAD --name-only | grep -q "requirements.txt"; then
    echo "📦 Обнаружены изменения в зависимостях, пересобираем образы..."
    docker-compose build --no-cache
else
    echo "🔄 Пересобираем образы..."
    docker-compose build
fi

# Запускаем обновленные контейнеры
echo "🚀 Запуск обновленных контейнеров..."
docker-compose up -d

# Ждем запуска
echo "⏳ Ожидание запуска сервисов..."
sleep 15

# Проверяем статус
echo "📊 Проверка статуса контейнеров:"
docker-compose ps

# Проверяем здоровье webhook
echo "🔍 Проверка webhook..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Webhook сервер работает"
else
    echo "⚠️ Webhook сервер может быть недоступен"
fi

# Показываем последние логи
echo "📝 Последние логи (10 строк):"
docker-compose logs --tail=10

echo ""
echo "✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО!"
echo ""
echo "📋 Полезные команды после обновления:"
echo "  Полные логи:     docker-compose logs -f"
echo "  Статус:          docker-compose ps"
echo "  Перезапуск:      docker-compose restart"
echo ""
echo "🔍 Если возникли проблемы:"
echo "  Откат:           git reset --hard HEAD~1 && docker-compose down && docker-compose up -d"
echo "  Восстановление:  cp $BACKUP_NAME data/okdesk_bot.db"
