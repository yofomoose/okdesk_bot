# Скрипт развертывания Okdesk Bot на Windows сервере

Write-Host "🚀 РАЗВЕРТЫВАНИЕ OKDESK BOT" -ForegroundColor Green
Write-Host "==========================" -ForegroundColor Green

# Проверяем наличие Docker
try {
    $dockerVersion = docker --version
    Write-Host "✅ Docker обнаружен: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker не установлен. Установите Docker Desktop и попробуйте снова." -ForegroundColor Red
    exit 1
}

# Проверяем наличие .env файла
if (-not (Test-Path ".env")) {
    Write-Host "❌ Файл .env не найден" -ForegroundColor Red
    Write-Host "💡 Создайте .env файл на основе .env.example:" -ForegroundColor Yellow
    Write-Host "   copy .env.example .env" -ForegroundColor Yellow
    Write-Host "   notepad .env" -ForegroundColor Yellow
    exit 1
}

# Создаем директорию для данных
if (-not (Test-Path "data")) {
    New-Item -ItemType Directory -Path "data" | Out-Null
    Write-Host "✅ Создана директория data/" -ForegroundColor Green
}

# Останавливаем существующие контейнеры
Write-Host "🛑 Остановка существующих контейнеров..." -ForegroundColor Yellow
docker-compose down

# Собираем образы
Write-Host "🔨 Сборка Docker образов..." -ForegroundColor Yellow
docker-compose build

# Запускаем контейнеры
Write-Host "🚀 Запуск контейнеров..." -ForegroundColor Yellow
docker-compose up -d

# Ждем запуска
Write-Host "⏳ Ожидание запуска сервисов..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Проверяем статус
Write-Host "📊 Статус контейнеров:" -ForegroundColor Cyan
docker-compose ps

# Проверяем логи
Write-Host "📝 Последние логи:" -ForegroundColor Cyan
docker-compose logs --tail=20

Write-Host ""
Write-Host "✅ РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Полезные команды:" -ForegroundColor Cyan
Write-Host "  Логи:           docker-compose logs -f"
Write-Host "  Статус:         docker-compose ps"
Write-Host "  Остановка:      docker-compose down"
Write-Host "  Перезапуск:     docker-compose restart"
Write-Host ""
Write-Host "🌐 Webhook доступен по адресу: http://localhost:8000/okdesk-webhook" -ForegroundColor Yellow
Write-Host "🔍 Проверка здоровья: curl http://localhost:8000/health" -ForegroundColor Yellow
