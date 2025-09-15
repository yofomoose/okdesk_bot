# 🚨 ИСПРАВЛЕНИЕ ПРОБЛЕМЫ "READONLY DATABASE"

## 📋 Диагностика проблемы

Ошибка `attempt to write a readonly database` означает, что SQLite база данных открыта в режиме "только чтение". Это может происходить по следующим причинам:

1. **Неправильные права доступа к файлу**
2. **Поврежденный файл базы данных**
3. **Проблемы с Docker volumes**
4. **Файловая система в режиме read-only**

## 🔍 Шаг 1: Диагностика

### Автоматическая диагностика
```bash
# Запустите диагностический скрипт
./diagnose-db.sh
```

### Ручная проверка
```bash
# Проверьте права доступа
ls -la ./data/okdesk_bot.db

# Проверьте директорию
ls -ld ./data/

# Проверьте, можно ли записать в файл
echo "test" >> ./data/test.txt && rm ./data/test.txt && echo "OK" || echo "ERROR"
```

## 🔧 Шаг 2: Исправление проблем

### Вариант 1: Исправление прав доступа (самый частый случай)
```bash
# Исправьте права на файл базы данных
chmod 666 ./data/okdesk_bot.db

# Исправьте права на директорию
chmod 755 ./data

# Проверьте результат
ls -la ./data/okdesk_bot.db
```

### Вариант 2: Пересоздание базы данных
```bash
# Создайте резервную копию
cp ./data/okdesk_bot.db ./data/okdesk_bot.db.backup

# Удалите поврежденный файл
rm ./data/okdesk_bot.db

# Перезапустите контейнеры (база создастся автоматически)
docker-compose restart
```

### Вариант 3: Проверка Docker конфигурации
```bash
# Проверьте монтирование volumes
docker-compose config

# Проверьте, что volume доступен для записи
docker-compose exec bot ls -la /app/data/

# Проверьте права внутри контейнера
docker-compose exec bot chmod 666 /app/data/okdesk_bot.db
```

## 🚀 Шаг 3: Перезапуск сервисов

```bash
# Остановите сервисы
docker-compose down

# Очистите кэш (опционально)
docker system prune -f

# Запустите сервисы
docker-compose up -d

# Проверьте статус
docker-compose ps
```

## 📊 Шаг 4: Проверка исправления

```bash
# Проверьте логи
docker-compose logs bot --tail=20

# Проверьте, что база данных работает
docker-compose exec bot python -c "
import sqlite3
conn = sqlite3.connect('/app/data/okdesk_bot.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM users')
print('Users count:', cursor.fetchone()[0])
conn.close()
print('Database OK')
"
```

## 🛠️ Быстрые команды исправления

### Для Linux/Mac:
```bash
# Исправление прав и перезапуск
chmod 666 ./data/okdesk_bot.db && chmod 755 ./data && docker-compose restart
```

### Для Windows (в контейнере):
```bash
# В контейнере исправьте права
docker-compose exec bot chmod 666 /app/data/okdesk_bot.db
docker-compose exec bot chmod 755 /app/data
docker-compose restart
```

## 🔍 Дополнительная диагностика

### Если проблема сохраняется:

1. **Проверьте дисковое пространство:**
```bash
df -h
```

2. **Проверьте файловую систему:**
```bash
mount | grep -E "(data|overlay)"
```

3. **Проверьте SELinux/AppArmor:**
```bash
# Для Ubuntu/Debian
sudo aa-status | grep docker
# Для CentOS/RHEL
sestatus
```

4. **Проверьте Docker logs:**
```bash
docker-compose logs --tail=50
```

## 📋 Контрольный список исправления

- [ ] Проверить права доступа: `ls -la ./data/okdesk_bot.db`
- [ ] Исправить права: `chmod 666 ./data/okdesk_bot.db`
- [ ] Перезапустить сервисы: `docker-compose restart`
- [ ] Проверить логи: `docker-compose logs bot --tail=10`
- [ ] Протестировать запись в БД

## 🚨 Если ничего не помогает

### Создание новой базы данных:
```bash
# Полностью очистить
docker-compose down -v
rm -rf ./data/*
docker system prune -f

# Пересоздать
docker-compose up -d

# Проверить
docker-compose logs bot
```

### Альтернативная конфигурация:
```yaml
# В docker-compose.yml изменить volumes
volumes:
  - ./data:/app/data:rw
  # или
  - ./data:/app/data:Z  # для SELinux
```

## 📞 Поддержка

Если проблема сохраняется:
1. Соберите полную информацию: `./diagnose-db.sh`
2. Проверьте логи Docker: `docker-compose logs`
3. Проверьте системные логи: `dmesg | tail -20`

---

**🎯 Чаще всего проблема решается простым исправлением прав доступа!**