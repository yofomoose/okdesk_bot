@echo off
echo 🚀 Установка Okdesk Telegram Bot
echo ================================

echo 📦 Проверка Python...
python --version
if %errorlevel% neq 0 (
    echo ❌ Python не найден! Установите Python 3.8 или выше
    pause
    exit /b 1
)

echo 🔧 Создание виртуального окружения...
python -m venv venv
if %errorlevel% neq 0 (
    echo ❌ Ошибка создания виртуального окружения
    pause
    exit /b 1
)

echo 🔌 Активация виртуального окружения...
call venv\Scripts\activate.bat

echo 📚 Установка зависимостей...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ❌ Ошибка установки зависимостей
    pause
    exit /b 1
)

echo 📋 Копирование файла конфигурации...
if not exist .env (
    copy .env.example .env
    echo ⚠️  Файл .env создан из примера
    echo 🔧 Отредактируйте .env файл, добавив ваши токены:
    echo    - BOT_TOKEN
    echo    - OKDESK_API_URL  
    echo    - OKDESK_API_TOKEN
) else (
    echo ℹ️  Файл .env уже существует
)

echo.
echo ✅ Установка завершена!
echo 🚀 Для запуска используйте: python start.py
echo 📖 Подробная инструкция в README.md
echo.
pause
