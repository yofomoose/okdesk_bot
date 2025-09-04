#!/bin/bash

echo "🔄 Настройка интеграции с Traefik..."

# Проверяем существование сети n8n
if ! docker network ls | grep -q "n8n_default"; then
    echo "❌ Сеть n8n_default не найдена!"
    echo "📋 Доступные сети:"
    docker network ls
    echo ""
    echo "🔧 Создаем сеть или проверьте имя сети n8n:"
    # docker network create n8n_default
    echo "Возможно сеть называется по-другому. Проверьте: docker network ls"
    exit 1
fi

# Остановка других версий
echo "🛑 Остановка других версий..."
docker-compose down 2>/dev/null
docker-compose -f docker-compose.with-npm.yml down 2>/dev/null
docker-compose -f docker-compose.npm-alt-ports.yml down 2>/dev/null

# Запуск с Traefik
echo "🚀 Запуск с интеграцией Traefik..."
docker-compose -f docker-compose.traefik.yml up -d --build

echo "⏳ Ожидание запуска..."
sleep 15

echo "📊 Статус контейнеров:"
docker-compose -f docker-compose.traefik.yml ps

echo ""
echo "🔍 Проверка интеграции с Traefik..."
docker inspect okdesk_bot_okdesk_webhook_1 --format='{{range $key, $value := .Config.Labels}}{{$key}}={{$value}}{{"\n"}}{{end}}' | grep traefik

echo ""
echo "✅ Интеграция с Traefik завершена!"
echo ""
echo "📌 Информация:"
echo "   • Webhook URL: https://okbot.teftelyatun.ru/okdesk-webhook"
echo "   • SSL сертификат: автоматически через Let's Encrypt (Traefik)"
echo "   • HTTP автоматически перенаправляется на HTTPS"
echo ""
echo "🔧 Проверка через 30-60 секунд:"
echo "   curl -I https://okbot.teftelyatun.ru/health"
echo ""
echo "📋 Если возникают проблемы, запустите:"
echo "   ./check-traefik.sh"
echo ""
