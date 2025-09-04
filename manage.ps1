# OKDesk Bot Management Script for Windows PowerShell
# Версия: 2.0 с исправлением базы данных

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

# Цвета для вывода
$Colors = @{
    Red = "Red"
    Green = "Green" 
    Yellow = "Yellow"
    Blue = "Blue"
    White = "White"
}

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Colors[$Color]
}

function Show-Help {
    Write-ColorOutput "OKDesk Bot Management Commands (Windows)" "Blue"
    Write-ColorOutput "=======================================" "Blue"
    Write-ColorOutput ""
    Write-ColorOutput "start        - Запустить все сервисы" "Green"
    Write-ColorOutput "stop         - Остановить все сервисы" "Green"
    Write-ColorOutput "restart      - Перезапустить сервисы" "Green"
    Write-ColorOutput "logs         - Показать логи" "Green"
    Write-ColorOutput "status       - Показать статус сервисов" "Green"
    Write-ColorOutput "diagnose     - Полная диагностика системы" "Green"
    Write-ColorOutput "update       - Обновить и перезапустить" "Green"
    Write-ColorOutput "backup       - Создать резервную копию БД" "Green"
    Write-ColorOutput "restore      - Восстановить из резервной копии" "Green"
    Write-ColorOutput "test         - Тестирование системы" "Green"
    Write-ColorOutput "clean        - Очистить неиспользуемые ресурсы" "Green"
    Write-ColorOutput ""
    Write-ColorOutput "Использование: .\manage.ps1 [команда]" "Yellow"
}

function Start-Services {
    Write-ColorOutput "Запуск сервисов..." "Yellow"
    
    # Проверяем файл .env
    if (!(Test-Path ".env")) {
        Write-ColorOutput "Файл .env не найден! Копирую из .env.example" "Red"
        Copy-Item ".env.example" ".env"
        Write-ColorOutput "Отредактируйте файл .env перед запуском" "Yellow"
    }
    
    # Создаем директории
    if (!(Test-Path "data")) { New-Item -ItemType Directory -Path "data" }
    if (!(Test-Path "backups")) { New-Item -ItemType Directory -Path "backups" }
    
    docker-compose up -d
    Write-ColorOutput "Сервисы запущены" "Green"
    Show-Status
}

function Stop-Services {
    Write-ColorOutput "Остановка сервисов..." "Yellow"
    docker-compose down
    Write-ColorOutput "Сервисы остановлены" "Green"
}

function Restart-Services {
    Write-ColorOutput "Перезапуск сервисов..." "Yellow"
    Stop-Services
    Start-Services
}

function Show-Logs {
    Write-ColorOutput "Показать логи (Ctrl+C для выхода)..." "Yellow"
    docker-compose logs -f
}

function Show-Status {
    Write-ColorOutput "Статус сервисов:" "Blue"
    docker-compose ps
    Write-ColorOutput ""
    Write-ColorOutput "Использование ресурсов:" "Blue"
    docker stats --no-stream --format "table {{.Name}}`t{{.CPUPerc}}`t{{.MemUsage}}" | Where-Object { $_ -match "okdesk" }
}

function Start-Diagnose {
    Write-ColorOutput "===========================================" "Blue"
    Write-ColorOutput "        ДИАГНОСТИКА СИСТЕМЫ OKDESK BOT" "Blue"  
    Write-ColorOutput "===========================================" "Blue"
    Write-ColorOutput ""
    
    # 1. Проверка файлов конфигурации
    Write-ColorOutput "1. Проверка файлов конфигурации:" "Yellow"
    if (Test-Path ".env") {
        Write-ColorOutput "✓ .env файл найден" "Green"
    } else {
        Write-ColorOutput "✗ .env файл отсутствует" "Red"
    }
    Write-ColorOutput ""
    
    # 2. Проверка Docker
    Write-ColorOutput "2. Проверка Docker:" "Yellow"
    try {
        $dockerVersion = docker --version
        Write-ColorOutput "✓ Docker установлен: $dockerVersion" "Green"
        
        $composeVersion = docker-compose --version
        Write-ColorOutput "✓ Docker Compose доступен: $composeVersion" "Green"
    } catch {
        Write-ColorOutput "✗ Docker или Docker Compose не установлен" "Red"
    }
    Write-ColorOutput ""
    
    # 3. Статус контейнеров
    Write-ColorOutput "3. Статус контейнеров:" "Yellow"
    docker-compose ps
    Write-ColorOutput ""
    
    # 4. Проверка базы данных
    Write-ColorOutput "4. Проверка базы данных:" "Yellow"
    if (Test-Path "data\okdesk_bot.db") {
        Write-ColorOutput "✓ База данных найдена: data\okdesk_bot.db" "Green"
        $dbSize = (Get-Item "data\okdesk_bot.db").Length
        $dbSizeKb = [math]::Round($dbSize / 1024, 1)
        Write-ColorOutput "Размер: $dbSizeKb KB" "Blue"
        
        $dbModified = (Get-Item "data\okdesk_bot.db").LastWriteTime
        Write-ColorOutput "Последнее изменение: $dbModified" "Blue"
    } else {
        Write-ColorOutput "✗ База данных не найдена" "Red"
    }
    Write-ColorOutput ""
    
    # 5. Проверка портов
    Write-ColorOutput "5. Проверка портов:" "Yellow"
    try {
        $port8000 = netstat -an | Select-String ":8000 "
        if ($port8000) {
            Write-ColorOutput "✓ Порт 8000 (webhook) занят" "Green"
        } else {
            Write-ColorOutput "✗ Порт 8000 свободен (webhook не запущен)" "Red"
        }
    } catch {
        Write-ColorOutput "Не удалось проверить порты" "Yellow"
    }
    Write-ColorOutput ""
    
    # 6. Проверка логов
    Write-ColorOutput "6. Проверка логов (последние 5 строк):" "Yellow"
    Write-ColorOutput "Bot logs:" "Blue"
    docker-compose logs --tail=5 bot 2>$null
    Write-ColorOutput ""
    Write-ColorOutput "Webhook logs:" "Blue"
    docker-compose logs --tail=5 webhook 2>$null
    Write-ColorOutput ""
    
    # 7. Проверка API
    Write-ColorOutput "7. Проверка доступности API:" "Yellow"
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/okdesk-webhook" -Method GET -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 405 -or $response.StatusCode -eq 200) {
            Write-ColorOutput "✓ Webhook API доступен" "Green"
        } else {
            Write-ColorOutput "✗ Webhook API недоступен" "Red"
        }
    } catch {
        Write-ColorOutput "✗ Webhook API недоступен" "Red"
    }
    Write-ColorOutput ""
    
    # 8. Запуск Python диагностики
    Write-ColorOutput "8. Расширенная диагностика:" "Yellow"
    if (Test-Path "full_diagnose.py") {
        python full_diagnose.py
    } else {
        Write-ColorOutput "Скрипт full_diagnose.py не найден" "Yellow"
    }
    
    Write-ColorOutput "===========================================" "Blue"
    Write-ColorOutput "           ДИАГНОСТИКА ЗАВЕРШЕНА" "Blue"
    Write-ColorOutput "===========================================" "Blue"
}

function Update-Services {
    Write-ColorOutput "Обновление сервисов..." "Yellow"
    git pull origin main 2>$null
    Stop-Services
    docker-compose build --no-cache
    Start-Services
    Start-Tests
    Write-ColorOutput "Обновление завершено" "Green"
}

function Backup-Database {
    Write-ColorOutput "Создание резервной копии..." "Yellow"
    
    if (!(Test-Path "backups")) { New-Item -ItemType Directory -Path "backups" }
    
    if (Test-Path "data\okdesk_bot.db") {
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $backupFile = "backups\okdesk_bot_$timestamp.db"
        Copy-Item "data\okdesk_bot.db" $backupFile
        Write-ColorOutput "✓ Резервная копия создана: $backupFile" "Green"
        
        # Показываем последние 5 резервных копий
        Get-ChildItem "backups\*.db" | Sort-Object LastWriteTime -Descending | Select-Object -First 5 | Format-Table Name, LastWriteTime, Length
    } else {
        Write-ColorOutput "✗ База данных не найдена для создания резервной копии" "Red"
    }
}

function Restore-Database {
    Write-ColorOutput "Доступные резервные копии:" "Yellow"
    $backups = Get-ChildItem "backups\*.db" -ErrorAction SilentlyContinue
    
    if ($backups) {
        $backups | Sort-Object LastWriteTime -Descending | Format-Table Name, LastWriteTime, Length
        
        $backupFile = Read-Host "Введите имя файла резервной копии"
        $fullPath = "backups\$backupFile"
        
        if (Test-Path $fullPath) {
            Copy-Item $fullPath "data\okdesk_bot.db"
            Write-ColorOutput "✓ База данных восстановлена из $backupFile" "Green"
        } else {
            Write-ColorOutput "✗ Файл резервной копии не найден" "Red"
        }
    } else {
        Write-ColorOutput "Резервные копии не найдены" "Red"
    }
}

function Start-Tests {
    Write-ColorOutput "Запуск тестирования..." "Yellow"
    
    # Проверка конфигурации
    Write-ColorOutput "Проверка конфигурации..." "Blue"
    if (Test-Path "check_config.py") {
        python check_config.py
    }
    
    # Проверка базы данных
    Write-ColorOutput "Проверка базы данных..." "Blue"
    if (Test-Path "data\okdesk_bot.db") {
        Write-ColorOutput "✓ База данных найдена" "Green"
    } else {
        Write-ColorOutput "✗ База данных не найдена" "Red"
    }
    
    # Проверка API
    Write-ColorOutput "Проверка API..." "Blue"
    if (Test-Path "test_api.py") {
        python test_api.py
    }
    
    Write-ColorOutput "Тестирование завершено" "Green"
}

function Clean-Resources {
    Write-ColorOutput "Очистка неиспользуемых ресурсов..." "Yellow"
    docker system prune -f
    docker volume prune -f
    Write-ColorOutput "Очистка завершена" "Green"
}

# Главная логика
switch ($Command.ToLower()) {
    "help" { Show-Help }
    "start" { Start-Services }
    "stop" { Stop-Services }
    "restart" { Restart-Services }
    "logs" { Show-Logs }
    "status" { Show-Status }
    "diagnose" { Start-Diagnose }
    "update" { Update-Services }
    "backup" { Backup-Database }
    "restore" { Restore-Database }
    "test" { Start-Tests }
    "clean" { Clean-Resources }
    default { 
        Write-ColorOutput "Неизвестная команда: $Command" "Red"
        Write-ColorOutput "Используйте '.\manage.ps1 help' для справки" "Yellow"
    }
}
