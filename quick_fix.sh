#!/bin/bash

echo "🔄 Быстрое обновление OKDesk Bot..."

# Остановка контейнеров
echo "⏹️ Останавливаем контейнеры..."
docker-compose down

# Пересборка с новыми исправлениями
echo "🔨 Пересборка с исправлениями регистрации..."
docker-compose build --no-cache

# Запуск
echo "▶️ Запуск обновленных контейнеров..."
docker-compose up -d

# Небольшая пауза для запуска
sleep 5

# Проверка логов
echo "📋 Проверка логов webhook (путь к БД):"
docker-compose logs webhook | head -5

echo ""
echo "📋 Проверка логов бота:"
docker-compose logs bot | tail -3

echo ""
echo "✅ Обновление завершено!"
echo ""
echo "🧪 Теперь можете протестировать:"
echo "1. Отправьте /start в бот - должно показать меню вместо регистрации"
echo "2. Добавьте комментарий в Okdesk - должно прийти уведомление в Telegram"
echo ""
echo "📊 Мониторинг логов:"
echo "docker-compose logs -f     # Все логи"
echo "docker-compose logs -f webhook  # Только webhook"
