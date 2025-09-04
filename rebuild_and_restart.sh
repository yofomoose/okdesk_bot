#!/bin/bash
echo "🔄 Остановка контейнеров..."
docker-compose down

echo "🛠️ Пересборка образов с новой конфигурацией..."
docker-compose build --no-cache

echo "🚀 Запуск обновленных контейнеров..."
docker-compose up -d

echo "📊 Проверка статуса..."
docker-compose ps

echo "📋 Показываем логи webhook для проверки пути БД..."
sleep 3
docker-compose logs webhook | tail -10

echo "✅ Готово! Попробуйте снова добавить комментарий в Okdesk"
