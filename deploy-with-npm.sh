#!/bin/bash

# Скрипт развертывания с Nginx Proxy Manager
echo "🚀 Развертывание OKDesk Bot с Nginx Proxy Manager..."

# Остановка существующих контейнеров
echo "⏹️ Остановка существующих контейнеров..."
docker-compose down 2>/dev/null || true
docker-compose -f docker-compose.with-npm.yml down 2>/dev/null || true

# Создание директорий для данных
echo "📁 Создание директорий..."
mkdir -p ./data/npm
mkdir -p ./data/letsencrypt

# Сборка и запуск с NPM
echo "🔨 Сборка и запуск контейнеров с NPM..."
docker-compose -f docker-compose.with-npm.yml up -d --build

# Ожидание запуска
echo "⏳ Ожидание запуска сервисов..."
sleep 10

# Проверка статуса
echo "📊 Статус контейнеров:"
docker-compose -f docker-compose.with-npm.yml ps

echo ""
echo "✅ Развертывание завершено!"
echo ""
echo "📌 Доступ к сервисам:"
echo "   • NPM Admin Panel: http://your-server-ip:81"
echo "   • Default login: admin@example.com / changeme"
echo "   • Webhook (internal): http://okdesk_webhook:8000"
echo ""
echo "🔧 Следующие шаги:"
echo "   1. Откройте http://your-server-ip:81"
echo "   2. Войдите с default credentials"
echo "   3. Смените пароль"
echo "   4. Добавьте proxy host для okbot.teftelyatun.ru → okdesk_webhook:8000"
echo "   5. Настройте SSL сертификат Let's Encrypt"
echo ""
