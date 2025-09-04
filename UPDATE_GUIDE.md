# 🔄 ИНСТРУКЦИЯ ПО ОБНОВЛЕНИЮ БОТА

## 📝 Процесс обновления после изменений кода

### 1️⃣ Локальные изменения → GitHub

```bash
# Перейти в директорию проекта
cd "c:\Users\YofoY\Documents\Что то долго хранимое\OKD_mini\okdesk_bot"

# Проверить изменения
git status

# Добавить измененные файлы
git add .

# Сделать коммит с описанием изменений
git commit -m "Описание ваших изменений"

# Отправить на GitHub
git push origin master
```

### 2️⃣ Обновление на сервере (с Docker)

```bash
# Подключиться к серверу по SSH
ssh user@your-server.com

# Перейти в директорию бота
cd /path/to/okdesk_bot

# Получить последние изменения с GitHub
git pull origin master

# Пересобрать и перезапустить Docker контейнеры
docker-compose down
docker-compose build
docker-compose up -d

# Проверить логи
docker-compose logs -f
```

### 3️⃣ Обновление на сервере (без Docker)

```bash
# Подключиться к серверу
ssh user@your-server.com

# Перейти в директорию бота
cd /path/to/okdesk_bot

# Получить изменения
git pull origin master

# Обновить зависимости (если requirements.txt изменился)
pip install -r requirements.txt

# Перезапустить бота и webhook
pkill -f "python bot.py"
pkill -f "python webhook_server.py"

# Запустить заново
nohup python bot.py &
nohup python webhook_server.py &
```

## 🚀 БЫСТРЫЕ КОМАНДЫ

### Windows (локальная разработка):
```powershell
# Сохранить и отправить изменения
cd "c:\Users\YofoY\Documents\Что то долго хранимое\OKD_mini\okdesk_bot"
git add .
git commit -m "Update: описание изменений"
git push origin master
```

### Linux сервер (обновление):
```bash
# Быстрое обновление с Docker
cd /path/to/okdesk_bot
git pull && docker-compose down && docker-compose up -d --build
```

## 📋 ТИПОВЫЕ СЦЕНАРИИ ОБНОВЛЕНИЯ

### 🔧 Изменение кода бота
1. Редактируете файлы (`bot.py`, `handlers/`, `services/`)
2. Тестируете локально
3. Коммитите и пушите на GitHub
4. На сервере: `git pull && docker-compose restart`

### ⚙️ Изменение конфигурации
1. Обновляете `.env.example` (если нужно)
2. Коммитите изменения
3. На сервере: обновляете `.env` вручную
4. Перезапускаете контейнеры

### 📦 Добавление зависимостей
1. Добавляете в `requirements.txt`
2. Тестируете: `pip install -r requirements.txt`
3. Коммитите и пушите
4. На сервере: `docker-compose build && docker-compose up -d`

### 🐳 Изменение Docker конфигурации
1. Редактируете `Dockerfile` или `docker-compose.yml`
2. Коммитите изменения
3. На сервере: `docker-compose down && docker-compose up -d --build`

## 🔍 ПРОВЕРКА ПОСЛЕ ОБНОВЛЕНИЯ

```bash
# Проверить статус контейнеров
docker-compose ps

# Посмотреть логи
docker-compose logs -f bot
docker-compose logs -f webhook

# Проверить webhook
curl http://your-server:8000/health

# Проверить бота в Telegram
# Отправить /start боту
```

## ⚠️ ВАЖНЫЕ МОМЕНТЫ

### 🔒 Безопасность:
- Никогда не коммитьте файл `.env` с реальными токенами
- Всегда используйте `.env.example` для примеров

### 💾 Бэкапы:
- Перед обновлением делайте бэкап базы данных:
  ```bash
  docker-compose exec webhook cp /app/data/okdesk_bot.db /app/data/backup_$(date +%Y%m%d).db
  ```

### 🔄 Откат изменений:
- Если что-то пошло не так:
  ```bash
  git reset --hard HEAD~1  # откатить последний коммит
  docker-compose down && docker-compose up -d
  ```

## 📞 ГОРЯЧИЕ КЛАВИШИ

### Быстрое обновление (все в одной команде):
```bash
# Локально
git add . && git commit -m "Quick update" && git push

# На сервере  
git pull && docker-compose down && docker-compose up -d --build
```

### Просмотр изменений:
```bash
git log --oneline        # История коммитов
git diff                 # Текущие изменения
git status              # Статус файлов
```

## 🎯 АВТОМАТИЗАЦИЯ

Для частых обновлений можно создать скрипт `update.sh`:

```bash
#!/bin/bash
echo "🔄 Обновление Okdesk Bot..."
git pull origin master
docker-compose down
docker-compose build
docker-compose up -d
echo "✅ Обновление завершено!"
docker-compose ps
```

Тогда обновление будет одной командой: `./update.sh`
