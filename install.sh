#!/bin/bash

echo "🚀 Установка Okdesk Telegram Bot"
echo "================================"

echo "📦 Проверка Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден! Установите Python 3.8 или выше"
    exit 1
fi

python3 --version

echo "🔧 Создание виртуального окружения..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "❌ Ошибка создания виртуального окружения"
    exit 1
fi

echo "🔌 Активация виртуального окружения..."
source venv/bin/activate

echo "📚 Установка зависимостей..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ Ошибка установки зависимостей"
    exit 1
fi

echo "📋 Копирование файла конфигурации..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  Файл .env создан из примера"
    echo "🔧 Отредактируйте .env файл, добавив ваши токены:"
    echo "   - BOT_TOKEN"
    echo "   - OKDESK_API_URL"
    echo "   - OKDESK_API_TOKEN"
else
    echo "ℹ️  Файл .env уже существует"
fi

echo ""
echo "✅ Установка завершена!"
echo "🚀 Для запуска используйте: python start.py"
echo "📖 Подробная инструкция в README.md"
