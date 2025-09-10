# Скрипт для запуска тестов проверки исправлений в боте Okdesk
# Автоматически создает виртуальное окружение, устанавливает зависимости и запускает тесты

# Проверяем, запущен ли скрипт с повышенными привилегиями
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "Для установки виртуального окружения рекомендуется запустить скрипт от имени администратора" -ForegroundColor Yellow
    Write-Host "Продолжить без прав администратора? (y/N)" -ForegroundColor Yellow
    $response = Read-Host
    if ($response -ne "y") {
        exit
    }
}

# Определяем директорию скрипта
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Переходим в директорию проекта
Set-Location $scriptDir

# Функция для проверки успешности выполнения команды
function Test-LastExitCode {
    param (
        [string]$message = "Произошла ошибка при выполнении предыдущей команды"
    )
    if ($LASTEXITCODE -ne 0) {
        Write-Host $message -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

# Функция для красивого вывода заголовков
function Write-Header {
    param (
        [string]$text
    )
    Write-Host "`n============================================" -ForegroundColor Cyan
    Write-Host " $text" -ForegroundColor Cyan
    Write-Host "============================================" -ForegroundColor Cyan
}

Write-Header "Запуск проверки исправлений бота Okdesk"

# Проверяем, установлен ли Python
try {
    $pythonVersion = python --version
    Write-Host "Найден Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Python не установлен или не находится в PATH. Пожалуйста, установите Python 3.7+" -ForegroundColor Red
    exit 1
}

# Создаем виртуальное окружение, если его нет
if (-Not (Test-Path "venv")) {
    Write-Header "Создание виртуального окружения"
    python -m venv venv
    Test-LastExitCode "Не удалось создать виртуальное окружение"
    Write-Host "Виртуальное окружение создано" -ForegroundColor Green
} else {
    Write-Host "Виртуальное окружение уже существует" -ForegroundColor Green
}

# Активируем виртуальное окружение
Write-Host "Активация виртуального окружения..." -ForegroundColor Yellow
try {
    . .\venv\Scripts\Activate.ps1
    Write-Host "Виртуальное окружение активировано" -ForegroundColor Green
} catch {
    Write-Host "Не удалось активировать виртуальное окружение. Возможно, у вас отключено выполнение скриптов PowerShell." -ForegroundColor Red
    Write-Host "Попробуйте выполнить: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Yellow
    exit 1
}

# Устанавливаем зависимости
Write-Header "Установка зависимостей"
python -m pip install -r requirements.txt
Test-LastExitCode "Не удалось установить зависимости"
Write-Host "Зависимости установлены" -ForegroundColor Green

# Предлагаем варианты запуска тестов
Write-Header "Выберите режим проверки"
Write-Host "1. Быстрая проверка (рекомендуется)" -ForegroundColor Yellow
Write-Host "2. Полный набор тестов" -ForegroundColor Yellow
Write-Host "3. Только диагностические инструменты" -ForegroundColor Yellow
Write-Host "4. Полный набор тестов с подробным выводом" -ForegroundColor Yellow
Write-Host "5. Выход" -ForegroundColor Yellow

$choice = Read-Host "Выберите опцию (1-5)"

switch ($choice) {
    "1" {
        Write-Header "Запуск быстрой проверки"
        python quick_check_fixes.py
    }
    "2" {
        Write-Header "Запуск полного набора тестов"
        python run_all_tests.py
    }
    "3" {
        Write-Header "Запуск диагностических инструментов"
        python run_all_tests.py --diagnostic
    }
    "4" {
        Write-Header "Запуск полного набора тестов с подробным выводом"
        python run_all_tests.py --all --verbose
    }
    "5" {
        Write-Host "Выход" -ForegroundColor Yellow
        exit 0
    }
    default {
        Write-Host "Неверный выбор" -ForegroundColor Red
        exit 1
    }
}

# Проверяем результат выполнения
if ($LASTEXITCODE -eq 0) {
    Write-Header "ПРОВЕРКА ЗАВЕРШЕНА УСПЕШНО"
    Write-Host "Все тесты пройдены успешно!" -ForegroundColor Green
    Write-Host "Исправления работают корректно." -ForegroundColor Green
} else {
    Write-Header "ПРОВЕРКА ЗАВЕРШЕНА С ОШИБКАМИ"
    Write-Host "Некоторые тесты не пройдены." -ForegroundColor Red
    Write-Host "Пожалуйста, проверьте результаты выше или запустите тесты с опцией --verbose для получения подробной информации." -ForegroundColor Yellow
}

# Деактивируем виртуальное окружение
deactivate

Read-Host "Нажмите Enter для выхода"
