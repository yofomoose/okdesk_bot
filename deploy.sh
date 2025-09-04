#!/bin/bash

# Скрипт развертывания Okdesk Bot на сервере

echo "🚀 РАЗВЕРТЫВАНИЕ OKDESK BOT"
echo "=========================="

# Проверяем наличие Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker и попробуйте снова."
    exit 1
fi

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден"
    echo "💡 Создайте .env файл на основе .env.example:"
    echo "   cp .env.example .env"
    echo "   nano .env"
    exit 1
fi

# Создаем директорию для данных
mkdir -p data

# Останавливаем существующие контейнеры
echo "🛑 Остановка существующих контейнеров..."
docker-compose down

# Собираем образы
echo "🔨 Сборка Docker образов..."
docker-compose build

# Запускаем контейнеры
echo "🚀 Запуск контейнеров..."
docker-compose up -d

# Ждем запуска
echo "⏳ Ожидание запуска сервисов..."
sleep 10

# Проверяем статус
echo "📊 Статус контейнеров:"
docker-compose ps

# Проверяем логи
echo "📝 Последние логи:"
docker-compose logs --tail=20

echo ""
echo "✅ РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО!"
echo ""
echo "📋 Полезные команды:"
echo "  Логи:           docker-compose logs -f"
echo "  Статус:         docker-compose ps"
echo "  Остановка:      docker-compose down"
echo "  Перезапуск:     docker-compose restart"
echo ""
echo "🌐 Webhook доступен по адресу: http://localhost:8000/okdesk-webhook"
echo "🔍 Проверка здоровья: curl http://localhost:8000/health"
