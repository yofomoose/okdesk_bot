#!/bin/bash

echo "🔄 Миграция базы данных в постоянный том..."

# Проверяем существующую базу
if docker exec okdesk_bot_okdesk_bot_1 test -f /app/okdesk_bot.db 2>/dev/null; then
    echo "📋 Найдена существующая база данных в контейнере"
    
    # Создаем резервную копию
    echo "💾 Создание резервной копии..."
    docker exec okdesk_bot_okdesk_bot_1 cp /app/okdesk_bot.db /app/okdesk_bot.db.backup
    
    # Копируем базу в постоянный том
    echo "📁 Копирование базы в постоянный том..."
    docker exec okdesk_bot_okdesk_bot_1 mkdir -p /app/data
    docker exec okdesk_bot_okdesk_bot_1 cp /app/okdesk_bot.db /app/data/okdesk_bot.db
    
    echo "✅ База данных скопирована в постоянный том"
else
    echo "ℹ️  Существующая база не найдена - будет создана новая"
fi

# Остановка контейнеров
echo "🛑 Остановка контейнеров..."
docker-compose -f docker-compose.traefik.yml down

# Обновление с новым путем к базе
echo "🚀 Запуск с обновленной конфигурацией..."
docker-compose -f docker-compose.traefik.yml up -d --build

echo "⏳ Ожидание запуска..."
sleep 15

echo "📊 Статус контейнеров:"
docker-compose -f docker-compose.traefik.yml ps

echo ""
echo "🔍 Проверка базы данных..."
if docker exec okdesk_bot_okdesk_bot_1 test -f /app/data/okdesk_bot.db; then
    echo "✅ База данных находится в постоянном томе: /app/data/okdesk_bot.db"
    
    # Показываем размер базы
    echo "📊 Размер базы данных:"
    docker exec okdesk_bot_okdesk_bot_1 ls -lh /app/data/okdesk_bot.db
    
    # Проверяем таблицы
    echo "📋 Проверка таблиц в базе:"
    docker exec okdesk_bot_okdesk_bot_1 sqlite3 /app/data/okdesk_bot.db ".tables"
    
    echo ""
    echo "✅ Миграция завершена успешно!"
    echo "🔒 База данных теперь сохраняется между перезапусками контейнеров"
else
    echo "❌ Ошибка: база данных не найдена в постоянном томе"
fi

echo ""
echo "📋 Информация о томах:"
docker volume ls | grep bot_data || echo "Том bot_data не найден"

echo ""
echo "🔧 Полезные команды:"
echo "   • Просмотр логов бота: docker-compose -f docker-compose.traefik.yml logs okdesk_bot"
echo "   • Резервная копия базы: docker exec okdesk_bot_okdesk_bot_1 cp /app/data/okdesk_bot.db /app/data/backup_\$(date +%Y%m%d_%H%M%S).db"
echo "   • Восстановление базы: docker exec okdesk_bot_okdesk_bot_1 cp /app/data/backup_YYYYMMDD_HHMMSS.db /app/data/okdesk_bot.db"
echo ""
