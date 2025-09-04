#!/bin/bash

echo "🔧 Настройка прямого доступа через IP..."

# Обновляем .env файл
echo "📝 Обновляем webhook URL на прямой IP..."
sed -i 's|WEBHOOK_URL=.*|WEBHOOK_URL=http://188.225.72.33:8000/okdesk-webhook|g' .env

# Перезапускаем контейнеры
echo "🔄 Перезапуск с обновленной конфигурацией..."
docker-compose -f docker-compose.traefik.yml down
docker-compose up -d --build

echo "⏳ Ожидание запуска..."
sleep 10

echo "📊 Статус контейнеров:"
docker-compose ps

echo ""
echo "✅ Готово! Webhook доступен по:"
echo "   http://188.225.72.33:8000/okdesk-webhook"
echo ""
echo "🔧 Проверка:"
echo "   curl -I http://188.225.72.33:8000/health"
echo ""
