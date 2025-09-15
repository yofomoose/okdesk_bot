# 🚀 Инструкция по обновлению Okdesk Bot на сервере

## 📋 Предварительные требования

Убедитесь, что на сервере установлены:
- Docker (версия 20.10+)
- Docker Compose (версия 2.0+)
- Git
- curl (для проверки работоспособности)

## 📥 Шаг 1: Получение обновлений

### Вариант 1: Автоматическое обновление (рекомендуется)
```bash
cd /path/to/okdesk_bot
git pull origin master
```

### Вариант 2: Резервное копирование и обновление
```bash
cd /path/to/okdesk_bot

# Создание резервной копии
cp -r . ../okdesk_bot_backup_$(date +%Y%m%d_%H%M%S)

# Получение обновлений
git pull origin master
```

## 🐳 Шаг 2: Обновление Docker образов

### Вариант 1: Быстрая пересборка (с кэшированием)
```bash
# Остановка текущих контейнеров
docker-compose down

# Быстрая пересборка с использованием кэша
docker-compose build

# Запуск обновленных контейнеров
docker-compose up -d
```

### Вариант 2: Полная пересборка (без кэша)
```bash
# Остановка контейнеров
docker-compose down

# Полная пересборка без кэша (для чистоты)
docker-compose build --no-cache

# Запуск
docker-compose up -d
```

### Вариант 3: Использование Makefile (если доступен)
```bash
# Полное обновление через Makefile
make update

# Или по отдельности
make down
make build-no-cache
make up
```

## 🔍 Шаг 3: Проверка работоспособности

### Проверка статуса контейнеров
```bash
docker-compose ps
```

### Проверка логов
```bash
# Логи всех сервисов
docker-compose logs --tail=50

# Логи только бота
docker-compose logs bot --tail=20

# Логи только webhook
docker-compose logs webhook --tail=20
```

### Проверка webhook endpoint
```bash
# Проверка доступности webhook сервера
curl -s http://localhost:8000/

# Проверка health check
curl -s http://localhost:8000/health || echo "Health check failed"
```

### Проверка Telegram бота
```bash
# Проверка токена бота (если есть .env файл)
grep BOT_TOKEN .env
```

## 🧹 Шаг 4: Очистка (опционально)

### Очистка неиспользуемых ресурсов
```bash
# Очистка остановленных контейнеров
docker container prune -f

# Очистка неиспользуемых образов
docker image prune -f

# Очистка кэша сборки
docker builder prune -f
```

### Полная оптимизация
```bash
# Остановка всего
docker-compose down

# Очистка системы
docker system prune -f

# Перезапуск
docker-compose up -d
```

## 📊 Шаг 5: Мониторинг после обновления

### Просмотр статистики
```bash
# Статистика использования ресурсов
docker stats

# Размеры образов
docker images

# Использование диска
docker system df
```

### Настройка логирования
```bash
# Просмотр логов в реальном времени
docker-compose logs -f

# Сохранение логов в файл
docker-compose logs > logs_$(date +%Y%m%d_%H%M%S).log
```

## 🚨 Шаг 6: Устранение неполадок

### Если контейнеры не запускаются
```bash
# Подробные логи сборки
docker-compose build --no-cache --progress=plain

# Проверка переменных окружения
docker-compose config

# Ручной запуск для отладки
docker-compose up bot
```

### Если webhook недоступен
```bash
# Проверка портов
netstat -tlnp | grep :8000

# Проверка логов webhook
docker-compose logs webhook

# Ручная проверка
curl -v http://localhost:8000/
```

### Если бот не отвечает
```bash
# Проверка токена
docker-compose exec bot python -c "import config; print('Token OK' if config.BOT_TOKEN else 'Token missing')"

# Проверка сетевых подключений
docker-compose exec bot curl -s https://api.telegram.org/bot${BOT_TOKEN}/getMe
```

## 🔄 Шаг 7: Автоматизация обновлений (рекомендуется)

### Создание скрипта автоматического обновления
```bash
#!/bin/bash
# auto-update.sh

echo "🚀 Начинаем автоматическое обновление..."

# Переход в директорию проекта
cd /path/to/okdesk_bot

# Получение обновлений
git pull origin master

# Остановка
docker-compose down

# Пересборка
docker-compose build --no-cache

# Запуск
docker-compose up -d

# Проверка
sleep 10
if curl -s http://localhost:8000/ > /dev/null; then
    echo "✅ Обновление успешно!"
else
    echo "❌ Ошибка обновления!"
    exit 1
fi
```

### Настройка cron для автоматических обновлений
```bash
# Ежедневное обновление в 2:00 ночи
0 2 * * * /path/to/auto-update.sh >> /var/log/okdesk-update.log 2>&1
```

## 📋 Контрольный список обновления

- [ ] Резервное копирование данных
- [ ] Получение обновлений из Git
- [ ] Остановка контейнеров
- [ ] Пересборка образов
- [ ] Запуск контейнеров
- [ ] Проверка работоспособности
- [ ] Проверка логов
- [ ] Очистка (опционально)
- [ ] Настройка мониторинга

## 🎯 Быстрые команды для частого использования

```bash
# Полное обновление
git pull && docker-compose down && docker-compose build --no-cache && docker-compose up -d

# Быстрое обновление
git pull && docker-compose build && docker-compose up -d

# Проверка статуса
docker-compose ps && docker-compose logs --tail=10

# Перезапуск
docker-compose restart

# Очистка
docker system prune -f
```

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи: `docker-compose logs`
2. Проверьте статус: `docker-compose ps`
3. Проверьте переменные окружения: `docker-compose config`
4. Проверьте доступность webhook: `curl http://localhost:8000/`

---

**🎉 Успешного обновления!**