#!/bin/bash

echo "🔄 Запуск с простой интеграцией Traefik (HTTP)..."

# Остановка текущих версий
echo "🛑 Остановка..."
docker-compose -f docker-compose.traefik.yml down
docker-compose down 2>/dev/null

# Запуск простой версии
echo "🚀 Запуск простой версии..."
docker-compose -f docker-compose.traefik-simple.yml up -d --build

echo "⏳ Ожидание запуска..."
sleep 10

echo "📊 Статус контейнеров:"
docker-compose -f docker-compose.traefik-simple.yml ps

echo ""
echo "✅ Готово!"
echo ""
echo "📌 Webhook доступен по HTTP:"
echo "   http://okbot.teftelyatun.ru/okdesk-webhook"
echo ""
echo "🔧 Проверка:"
echo "   curl -I http://okbot.teftelyatun.ru/health"
echo ""
