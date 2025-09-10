#!/bin/bash

# Скрипт для применения исправления и быстрого развертывания бота

echo "🔧 Применение исправлений для Okdesk Bot"
echo "========================================"

# Проверяем наличие файла исправления
if [ -f "services/okdesk_api_fixed.py" ]; then
    echo "✅ Найден файл исправления"
else
    echo "❌ Файл исправления не найден"
    exit 1
fi

# Создаем резервную копию текущего файла
echo "📦 Создание резервной копии..."
cp services/okdesk_api.py services/okdesk_api.py.bak
echo "✅ Резервная копия создана: services/okdesk_api.py.bak"

# Применяем исправление
echo "🔄 Применение исправления..."
cp services/okdesk_api_fixed.py services/okdesk_api.py
echo "✅ Исправление применено"

# Перезапускаем контейнеры
echo "🚀 Перезапуск контейнеров..."
docker-compose down
docker-compose up -d --build

# Ожидаем запуска
echo "⏳ Ожидание запуска сервисов..."
sleep 10

# Проверяем логи
echo "📋 Последние логи бота:"
docker-compose logs --tail=20 bot

echo ""
echo "✅ Исправление успешно применено и развернуто!"
echo ""
echo "📝 Для мониторинга логов используйте команду:"
echo "   docker-compose logs -f"
