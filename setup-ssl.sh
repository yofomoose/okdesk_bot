#!/bin/bash

echo "🔐 Настройка SSL с отдельным Traefik..."

# Остановка других версий
echo "🛑 Остановка предыдущих версий..."
docker-compose -f docker-compose.traefik.yml down
docker-compose -f docker-compose.traefik-simple.yml down 2>/dev/null
docker-compose down 2>/dev/null

# Запуск с отдельным Traefik
echo "🚀 Запуск с SSL Traefik..."
docker-compose -f docker-compose.ssl.yml up -d --build

echo "⏳ Ожидание запуска и создания SSL сертификата..."
sleep 30

echo "📊 Статус контейнеров:"
docker-compose -f docker-compose.ssl.yml ps

echo ""
echo "🔍 Проверка SSL сертификата..."
sleep 15

# Проверяем создание сертификата
echo "📜 Логи создания сертификата:"
docker-compose -f docker-compose.ssl.yml logs traefik-ssl | grep -i "certificate\|acme\|letsencrypt" | tail -5

echo ""
echo "✅ SSL настройка завершена!"
echo ""
echo "📌 Доступ к сервисам:"
echo "   • Webhook HTTPS: https://okbot.teftelyatun.ru/okdesk-webhook"
echo "   • Webhook HTTP: http://okbot.teftelyatun.ru:8080/okdesk-webhook (редирект на HTTPS)"
echo "   • Traefik Dashboard: http://188.225.72.33:8888"
echo ""
echo "🔧 Проверка SSL:"
echo "   curl -I https://okbot.teftelyatun.ru/health"
echo ""
echo "📋 Порты:"
echo "   • 8080: HTTP (автоматический редирект на HTTPS)"
echo "   • 8443: HTTPS с SSL сертификатом"
echo "   • 8888: Traefik Dashboard"
echo ""
