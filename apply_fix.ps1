# Скрипт для применения исправления и быстрого развертывания бота в Windows PowerShell

Write-Host "🔧 Применение исправлений для Okdesk Bot" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Проверяем наличие файла исправления
if (Test-Path "services\okdesk_api_fixed.py") {
    Write-Host "✅ Найден файл исправления" -ForegroundColor Green
} else {
    Write-Host "❌ Файл исправления не найден" -ForegroundColor Red
    exit 1
}

# Создаем резервную копию текущего файла
Write-Host "📦 Создание резервной копии..." -ForegroundColor Yellow
Copy-Item "services\okdesk_api.py" -Destination "services\okdesk_api.py.bak"
Write-Host "✅ Резервная копия создана: services\okdesk_api.py.bak" -ForegroundColor Green

# Применяем исправление
Write-Host "🔄 Применение исправления..." -ForegroundColor Yellow
Copy-Item "services\okdesk_api_fixed.py" -Destination "services\okdesk_api.py"
Write-Host "✅ Исправление применено" -ForegroundColor Green

# Перезапускаем контейнеры
Write-Host "🚀 Перезапуск контейнеров..." -ForegroundColor Yellow
docker-compose down
docker-compose up -d --build

# Ожидаем запуска
Write-Host "⏳ Ожидание запуска сервисов..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Проверяем логи
Write-Host "📋 Последние логи бота:" -ForegroundColor Cyan
docker-compose logs --tail=20 bot

Write-Host ""
Write-Host "✅ Исправление успешно применено и развернуто!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Для мониторинга логов используйте команду:" -ForegroundColor Cyan
Write-Host "   docker-compose logs -f" -ForegroundColor White
