#!/bin/bash

echo "🔄 Переключение на Traefik (использование существующего reverse proxy)..."

# Остановка NPM
echo "🛑 Остановка NPM..."
docker-compose -f docker-compose.with-npm.yml down
docker-compose -f docker-compose.npm-alt-ports.yml down 2>/dev/null

# Запуск с Traefik
echo "🚀 Запуск с интеграцией Traefik..."
docker-compose -f docker-compose.traefik.yml up -d --build

echo "⏳ Ожидание запуска..."
sleep 10

echo "📊 Статус контейнеров:"
docker-compose -f docker-compose.traefik.yml ps

echo ""
echo "✅ Интеграция с Traefik завершена!"
echo ""
echo "📌 Информация:"
echo "   • Webhook URL: https://okbot.teftelyatun.ru/okdesk-webhook"
echo "   • SSL сертификат: автоматически через Let's Encrypt (Traefik)"
echo "   • Домен настроен в Traefik конфигурации"
echo ""
echo "🔧 Проверка:"
echo "   curl -I https://okbot.teftelyatun.ru/health"
echo ""
