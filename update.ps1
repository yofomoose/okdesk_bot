# Скрипт автоматического обновления Okdesk Bot на Windows сервере

Write-Host "🔄 ОБНОВЛЕНИЕ OKDESK BOT" -ForegroundColor Green
Write-Host "=======================" -ForegroundColor Green

# Проверяем наличие git репозитория
if (-not (Test-Path ".git")) {
    Write-Host "❌ Это не git репозиторий!" -ForegroundColor Red
    exit 1
}

# Получаем текущую ветку
$currentBranch = git branch --show-current
Write-Host "📍 Текущая ветка: $currentBranch" -ForegroundColor Cyan

# Проверяем подключение к GitHub
Write-Host "🌐 Проверяем подключение к GitHub..." -ForegroundColor Yellow
git fetch origin

# Проверяем есть ли обновления
$local = git rev-parse HEAD
$remote = git rev-parse "origin/$currentBranch"

if ($local -eq $remote) {
    Write-Host "✅ Код уже актуальный, обновления не требуются" -ForegroundColor Green
    exit 0
}

Write-Host "📥 Найдены обновления, начинаем процесс..." -ForegroundColor Yellow

# Создаем бэкап базы данных
if (Test-Path "data/okdesk_bot.db") {
    $backupName = "data/backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').db"
    Copy-Item "data/okdesk_bot.db" $backupName
    Write-Host "💾 Создан бэкап базы данных: $backupName" -ForegroundColor Green
}

# Останавливаем контейнеры
Write-Host "🛑 Остановка контейнеров..." -ForegroundColor Yellow
docker-compose down

# Получаем обновления
Write-Host "📥 Получение обновлений с GitHub..." -ForegroundColor Yellow
git pull origin $currentBranch

# Проверяем изменения в зависимостях
$changedFiles = git diff HEAD~1 HEAD --name-only
if ($changedFiles -contains "requirements.txt") {
    Write-Host "📦 Обнаружены изменения в зависимостях, пересобираем образы..." -ForegroundColor Yellow
    docker-compose build --no-cache
} else {
    Write-Host "🔄 Пересобираем образы..." -ForegroundColor Yellow
    docker-compose build
}

# Запускаем обновленные контейнеры
Write-Host "🚀 Запуск обновленных контейнеров..." -ForegroundColor Yellow
docker-compose up -d

# Ждем запуска
Write-Host "⏳ Ожидание запуска сервисов..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Проверяем статус
Write-Host "📊 Проверка статуса контейнеров:" -ForegroundColor Cyan
docker-compose ps

# Проверяем здоровье webhook
Write-Host "🔍 Проверка webhook..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5
    Write-Host "✅ Webhook сервер работает" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Webhook сервер может быть недоступен" -ForegroundColor Yellow
}

# Показываем последние логи
Write-Host "📝 Последние логи (10 строк):" -ForegroundColor Cyan
docker-compose logs --tail=10

Write-Host ""
Write-Host "✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Полезные команды после обновления:" -ForegroundColor Cyan
Write-Host "  Полные логи:     docker-compose logs -f"
Write-Host "  Статус:          docker-compose ps"
Write-Host "  Перезапуск:      docker-compose restart"
Write-Host ""
Write-Host "🔍 Если возникли проблемы:" -ForegroundColor Yellow
Write-Host "  Откат:           git reset --hard HEAD~1; docker-compose down; docker-compose up -d"
if ($backupName) {
    Write-Host "  Восстановление:  Copy-Item '$backupName' 'data/okdesk_bot.db'"
}
