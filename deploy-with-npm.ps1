# Скрипт развертывания с Nginx Proxy Manager для Windows
Write-Host "🚀 Развертывание OKDesk Bot с Nginx Proxy Manager..." -ForegroundColor Green

# Остановка существующих контейнеров
Write-Host "⏹️ Остановка существующих контейнеров..." -ForegroundColor Yellow
docker-compose down 2>$null
docker-compose -f docker-compose.with-npm.yml down 2>$null

# Создание директорий для данных
Write-Host "📁 Создание директорий..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path ".\data\npm" -Force | Out-Null
New-Item -ItemType Directory -Path ".\data\letsencrypt" -Force | Out-Null

# Сборка и запуск с NPM
Write-Host "🔨 Сборка и запуск контейнеров с NPM..." -ForegroundColor Yellow
docker-compose -f docker-compose.with-npm.yml up -d --build

# Ожидание запуска
Write-Host "⏳ Ожидание запуска сервисов..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Проверка статуса
Write-Host "📊 Статус контейнеров:" -ForegroundColor Yellow
docker-compose -f docker-compose.with-npm.yml ps

Write-Host ""
Write-Host "✅ Развертывание завершено!" -ForegroundColor Green
Write-Host ""
Write-Host "📌 Доступ к сервисам:" -ForegroundColor Cyan
Write-Host "   • NPM Admin Panel: http://188.225.72.33:81" -ForegroundColor White
Write-Host "   • Default login: admin@example.com / changeme" -ForegroundColor White
Write-Host "   • Webhook (internal): http://okdesk_webhook:8000" -ForegroundColor White
Write-Host ""
Write-Host "🔧 Следующие шаги:" -ForegroundColor Cyan
Write-Host "   1. Откройте http://188.225.72.33:81" -ForegroundColor White
Write-Host "   2. Войдите с default credentials" -ForegroundColor White
Write-Host "   3. Смените пароль" -ForegroundColor White
Write-Host "   4. Добавьте proxy host для okbot.teftelyatun.ru → okdesk_webhook:8000" -ForegroundColor White
Write-Host "   5. Настройте SSL сертификат Let's Encrypt" -ForegroundColor White
Write-Host ""
