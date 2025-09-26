# PowerShell скрипт для развертывания обновлений с медиафайлами
# deploy_media_features.ps1

Write-Host "🚀 РАЗВЕРТЫВАНИЕ ОБНОВЛЕНИЙ МЕДИАФАЙЛОВ" -ForegroundColor Cyan
Write-Host "=" * 50 -ForegroundColor Gray

# Функция для выполнения команд
function Invoke-DeployCommand {
    param(
        [string]$Command,
        [string]$Description
    )
    
    Write-Host "🔄 $Description..." -ForegroundColor Yellow
    
    try {
        $result = Invoke-Expression $Command 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ $Description - успешно" -ForegroundColor Green
            if ($result) {
                Write-Host "   $result" -ForegroundColor Gray
            }
            return $true
        } else {
            Write-Host "❌ $Description - ошибка" -ForegroundColor Red
            if ($result) {
                Write-Host "   $result" -ForegroundColor Red
            }
            return $false
        }
    }
    catch {
        Write-Host "💥 $Description - исключение: $_" -ForegroundColor Red
        return $false
    }
}

# Проверяем наличие Docker
Write-Host "🔍 Проверка требований..." -ForegroundColor Cyan

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker не найден. Установите Docker Desktop и попробуйте снова." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "docker-compose.yml")) {
    Write-Host "❌ Файл docker-compose.yml не найден" -ForegroundColor Red
    Write-Host "   Запустите скрипт из корневой директории проекта" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Все требования выполнены" -ForegroundColor Green
Write-Host ""

# Этапы развертывания
$deploymentSteps = @(
    @("docker-compose down", "Остановка контейнеров"),
    @("docker-compose build --no-cache okdesk_bot", "Пересборка бота"),
    @("docker-compose up -d", "Запуск обновленных контейнеров"),
    @("docker-compose ps", "Проверка статуса контейнеров")
)

$successCount = 0

foreach ($step in $deploymentSteps) {
    $command = $step[0]
    $description = $step[1]
    
    if (Invoke-DeployCommand -Command $command -Description $description) {
        $successCount++
    } else {
        Write-Host ""
        Write-Host "❌ Развертывание остановлено на этапе: $description" -ForegroundColor Red
        Write-Host "🔧 Исправьте ошибку и попробуйте снова" -ForegroundColor Yellow
        exit 1
    }
    Write-Host ""
}

# Дополнительные проверки
Write-Host "🔍 ДОПОЛНИТЕЛЬНЫЕ ПРОВЕРКИ" -ForegroundColor Cyan
Write-Host "-" * 30 -ForegroundColor Gray

$additionalChecks = @(
    @("docker-compose logs --tail=10 okdesk_bot", "Последние логи бота"),
    @("docker-compose logs --tail=5 okdesk_webhook", "Логи webhook")
)

foreach ($check in $additionalChecks) {
    $command = $check[0]
    $description = $check[1]
    
    $null = Invoke-DeployCommand -Command $command -Description $description
    Write-Host ""
}

# Итоговый отчет
Write-Host "=" * 50 -ForegroundColor Gray
Write-Host "📊 ИТОГИ РАЗВЕРТЫВАНИЯ" -ForegroundColor Cyan
Write-Host "=" * 50 -ForegroundColor Gray

if ($successCount -eq $deploymentSteps.Count) {
    Write-Host "🎉 ВСЕ ЭТАПЫ РАЗВЕРТЫВАНИЯ ЗАВЕРШЕНЫ УСПЕШНО!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Новые функции активированы:" -ForegroundColor White
    Write-Host "   ✅ Поддержка медиафайлов в комментариях" -ForegroundColor Green
    Write-Host "   ✅ Улучшенный вывод сообщений" -ForegroundColor Green
    Write-Host "   ✅ Оптимизированная оценка заявок" -ForegroundColor Green
    Write-Host ""
    Write-Host "🧪 Для тестирования запустите:" -ForegroundColor White
    Write-Host "   python test_media_comments.py" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📱 Протестируйте в Telegram боте:" -ForegroundColor White
    Write-Host "   1. Создайте заявку" -ForegroundColor Gray
    Write-Host "   2. Добавьте комментарий с фото" -ForegroundColor Gray
    Write-Host "   3. Проверьте оценку заявки" -ForegroundColor Gray
} else {
    Write-Host "⚠️ РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО С ОШИБКАМИ" -ForegroundColor Yellow
    Write-Host "   Успешно: $successCount/$($deploymentSteps.Count) этапов" -ForegroundColor Red
    Write-Host "   Проверьте логи и исправьте ошибки" -ForegroundColor Red
}

Write-Host "=" * 50 -ForegroundColor Gray

# Ожидание нажатия клавиши
Write-Host ""
Write-Host "Нажмите любую клавишу для завершения..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")