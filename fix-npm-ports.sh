#!/bin/bash

# Остановка NPM с конфликтующими портами
echo "🛑 Остановка NPM контейнера..."
docker-compose -f docker-compose.with-npm.yml down

# Запуск с альтернативными портами
echo "🚀 Запуск NPM с альтернативными портами..."
docker-compose -f docker-compose.npm-alt-ports.yml up -d --build

echo "⏳ Ожидание запуска..."
sleep 10

echo "📊 Статус контейнеров:"
docker-compose -f docker-compose.npm-alt-ports.yml ps

echo ""
echo "✅ NPM запущен на альтернативных портах!"
echo ""
echo "📌 Доступ к сервисам:"
echo "   • NPM Admin Panel: http://188.225.72.33:81"
echo "   • NPM HTTP: http://188.225.72.33:8080"
echo "   • NPM HTTPS: https://188.225.72.33:8443"
echo ""
echo "⚠️  ВАЖНО: Используйте порт 8443 для HTTPS трафика"
echo "   Webhook URL: https://188.225.72.33:8443/okdesk-webhook"
echo ""
