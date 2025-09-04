# Управление базой данных OKDesk Bot

## Постоянное хранение базы данных

База данных теперь сохраняется в Docker volume `bot_data` и НЕ теряется при обновлениях контейнеров.

### Путь к базе данных:
- **В контейнере**: `/app/data/okdesk_bot.db`
- **Docker volume**: `bot_data`
- **Настройка в .env**: `DATABASE_URL=sqlite:////app/data/okdesk_bot.db`

## Миграция существующей базы

Если у вас уже есть база данных в старом месте, выполните:

```bash
chmod +x migrate-database.sh
./migrate-database.sh
```

Этот скрипт:
1. Найдет существующую базу данных
2. Создаст резервную копию
3. Переместит базу в постоянный том
4. Перезапустит контейнеры с новой конфигурацией

## Резервное копирование

### Ручное создание резервной копии:
```bash
chmod +x backup-database.sh
./backup-database.sh
```

### Автоматическое резервное копирование:
```bash
chmod +x setup-backup-cron.sh
./setup-backup-cron.sh
```

Настраивает ежедневное резервное копирование в 02:00.

## Восстановление из резервной копии

```bash
# Просмотр доступных резервных копий
docker exec okdesk_bot_okdesk_bot_1 ls -la /app/data/backups/

# Восстановление из резервной копии
docker exec okdesk_bot_okdesk_bot_1 cp /app/data/backups/okdesk_bot_backup_YYYYMMDD_HHMMSS.db /app/data/okdesk_bot.db

# Перезапуск контейнеров
docker-compose -f docker-compose.traefik.yml restart
```

## Проверка базы данных

```bash
# Проверка существования базы
docker exec okdesk_bot_okdesk_bot_1 test -f /app/data/okdesk_bot.db && echo "База существует" || echo "База не найдена"

# Размер базы данных
docker exec okdesk_bot_okdesk_bot_1 ls -lh /app/data/okdesk_bot.db

# Список таблиц в базе
docker exec okdesk_bot_okdesk_bot_1 sqlite3 /app/data/okdesk_bot.db ".tables"

# Количество записей в таблицах
docker exec okdesk_bot_okdesk_bot_1 sqlite3 /app/data/okdesk_bot.db "
SELECT 'users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'issues' as table_name, COUNT(*) as count FROM issues  
UNION ALL
SELECT 'comments' as table_name, COUNT(*) as count FROM comments;
"
```

## Экспорт/Импорт данных

### Экспорт в SQL:
```bash
docker exec okdesk_bot_okdesk_bot_1 sqlite3 /app/data/okdesk_bot.db .dump > okdesk_bot_export.sql
```

### Импорт из SQL:
```bash
# Создание новой базы из SQL файла
docker exec -i okdesk_bot_okdesk_bot_1 sqlite3 /app/data/okdesk_bot_new.db < okdesk_bot_export.sql

# Замена текущей базы
docker exec okdesk_bot_okdesk_bot_1 mv /app/data/okdesk_bot.db /app/data/okdesk_bot.db.old
docker exec okdesk_bot_okdesk_bot_1 mv /app/data/okdesk_bot_new.db /app/data/okdesk_bot.db
```

## Очистка старых данных

```bash
# Удаление старых комментариев (старше 6 месяцев)
docker exec okdesk_bot_okdesk_bot_1 sqlite3 /app/data/okdesk_bot.db "
DELETE FROM comments 
WHERE created_at < datetime('now', '-6 months');
"

# Вакуумизация базы для уменьшения размера
docker exec okdesk_bot_okdesk_bot_1 sqlite3 /app/data/okdesk_bot.db "VACUUM;"
```

## Мониторинг

### Логи работы с базой данных:
```bash
# Логи бота (включая SQL запросы)
docker-compose -f docker-compose.traefik.yml logs okdesk_bot | grep -i "sql\|database"

# Логи резервного копирования
tail -f /var/log/okdesk_backup.log
```

### Размер данных:
```bash
# Размер Docker volume
docker system df -v | grep bot_data

# Размер базы данных
docker exec okdesk_bot_okdesk_bot_1 du -h /app/data/
```

## Troubleshooting

### Проблема: База данных заблокирована
```bash
# Остановка всех контейнеров
docker-compose -f docker-compose.traefik.yml down

# Проверка блокировки
docker run --rm -v okdesk_bot_bot_data:/data alpine ls -la /data/

# Удаление lock файлов
docker run --rm -v okdesk_bot_bot_data:/data alpine rm -f /data/*.lock

# Перезапуск
docker-compose -f docker-compose.traefik.yml up -d
```

### Проблема: Поврежденная база данных
```bash
# Проверка целостности
docker exec okdesk_bot_okdesk_bot_1 sqlite3 /app/data/okdesk_bot.db "PRAGMA integrity_check;"

# Восстановление из резервной копии
docker exec okdesk_bot_okdesk_bot_1 cp /app/data/backups/okdesk_bot_backup_LATEST.db /app/data/okdesk_bot.db
```

## Безопасность

- ✅ База данных хранится в Docker volume (не в контейнере)
- ✅ Автоматические резервные копии
- ✅ Ротация старых резервных копий
- ✅ Возможность экспорта/импорта
- ⚠️ Рекомендуется дополнительное резервное копирование на внешний носитель
