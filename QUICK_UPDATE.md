# 🚀 БЫСТРЫЕ КОМАНДЫ ДЛЯ ОБНОВЛЕНИЯ БОТА

## 💻 Локальная разработка (Windows)

```powershell
# Перейти в папку проекта
cd "c:\Users\YofoY\Documents\Что то долго хранимое\OKD_mini\okdesk_bot"

# Сохранить изменения
git add .
git commit -m "Описание изменений"
git push origin master
```

## 🖥️ Обновление на сервере

### Автоматическое обновление:
```bash
# Linux/Mac
./update.sh

# Windows Server
.\update.ps1
```

### Ручное обновление:
```bash
# Быстрое обновление (одной командой)
git pull && docker-compose down && docker-compose up -d --build

# Пошаговое обновление
git pull origin master
docker-compose down
docker-compose build
docker-compose up -d
```

## 🔄 Типичные сценарии

### 1. Изменил код бота:
```bash
# Локально
git add . && git commit -m "Fix bot logic" && git push

# На сервере
git pull && docker-compose restart bot
```

### 2. Добавил новые зависимости:
```bash
# Локально (после изменения requirements.txt)
git add . && git commit -m "Add new dependencies" && git push

# На сервере
git pull && docker-compose build && docker-compose up -d
```

### 3. Изменил конфигурацию webhook:
```bash
# Локально
git add . && git commit -m "Update webhook config" && git push

# На сервере
git pull && docker-compose restart webhook
```

### 4. Полное обновление системы:
```bash
git pull && docker-compose down && docker-compose build --no-cache && docker-compose up -d
```

## 🔍 Проверка после обновления

```bash
# Статус контейнеров
docker-compose ps

# Логи всех сервисов
docker-compose logs -f

# Логи только бота
docker-compose logs -f bot

# Логи только webhook
docker-compose logs -f webhook

# Проверка webhook
curl http://localhost:8000/health

# Последние 50 строк логов
docker-compose logs --tail=50
```

## ⚠️ Если что-то пошло не так

### Откат к предыдущей версии:
```bash
git reset --hard HEAD~1
docker-compose down
docker-compose up -d
```

### Восстановление базы данных:
```bash
# Если есть бэкап
cp data/backup_YYYYMMDD_HHMMSS.db data/okdesk_bot.db
docker-compose restart
```

### Полная переустановка:
```bash
docker-compose down
docker system prune -a
git pull
docker-compose up -d --build
```

## 📋 Полезные алиасы

Добавьте в `~/.bashrc` или `~/.zshrc`:

```bash
# Okdesk Bot shortcuts
alias okbot-update='cd /path/to/okdesk_bot && ./update.sh'
alias okbot-logs='cd /path/to/okdesk_bot && docker-compose logs -f'
alias okbot-status='cd /path/to/okdesk_bot && docker-compose ps'
alias okbot-restart='cd /path/to/okdesk_bot && docker-compose restart'
```

Тогда можно будет просто писать:
- `okbot-update` - обновить бота
- `okbot-logs` - посмотреть логи
- `okbot-status` - статус контейнеров
- `okbot-restart` - перезапустить

## 🔔 Мониторинг

### Простая проверка здоровья:
```bash
#!/bin/bash
# health_check.sh
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Bot is healthy"
else
    echo "❌ Bot is down"
    # Перезапуск при необходимости
    docker-compose restart
fi
```

### Добавить в crontab для автоматической проверки:
```bash
# Проверять каждые 5 минут
*/5 * * * * /path/to/okdesk_bot/health_check.sh
```
