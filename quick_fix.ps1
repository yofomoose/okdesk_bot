# Быстрое исправление OKDesk Bot (Windows PowerShell)

Write-Host "🔄 Быстрое обновление OKDesk Bot..." -ForegroundColor Blue

# Остановка контейнеров
Write-Host "⏹️ Останавливаем контейнеры..." -ForegroundColor Yellow
docker-compose down

# Пересборка с новыми исправлениями
Write-Host "🔨 Пересборка с исправлениями регистрации..." -ForegroundColor Yellow
docker-compose build --no-cache

# Запуск
Write-Host "▶️ Запуск обновленных контейнеров..." -ForegroundColor Yellow
docker-compose up -d

# Небольшая пауза для запуска
Start-Sleep -Seconds 5

# Проверка логов
Write-Host "📋 Проверка логов webhook (путь к БД):" -ForegroundColor Cyan
docker-compose logs webhook | Select-Object -First 5

Write-Host ""
Write-Host "📋 Проверка логов бота:" -ForegroundColor Cyan
docker-compose logs bot | Select-Object -Last 3

Write-Host ""
Write-Host "✅ Обновление завершено!" -ForegroundColor Green
Write-Host ""
Write-Host "🧪 Теперь можете протестировать:" -ForegroundColor White
Write-Host "1. Отправьте /start в бот - должно показать меню вместо регистрации" -ForegroundColor White
Write-Host "2. Добавьте комментарий в Okdesk - должно прийти уведомление в Telegram" -ForegroundColor White
Write-Host ""
Write-Host "📊 Мониторинг логов:" -ForegroundColor White
Write-Host "docker-compose logs -f         # Все логи" -ForegroundColor Gray
Write-Host "docker-compose logs -f webhook # Только webhook" -ForegroundColor Gray
