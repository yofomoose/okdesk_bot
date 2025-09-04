#!/bin/bash

echo "⏰ Настройка автоматического резервного копирования..."

# Путь к скрипту резервного копирования
BACKUP_SCRIPT="/opt/okdesk_bot/backup-database.sh"
CRON_JOB="0 2 * * * cd /opt/okdesk_bot && ./backup-database.sh >> /var/log/okdesk_backup.log 2>&1"

# Проверяем существование скрипта
if [ ! -f "$BACKUP_SCRIPT" ]; then
    echo "❌ Ошибка: скрипт резервного копирования не найден: $BACKUP_SCRIPT"
    exit 1
fi

# Делаем скрипт исполняемым
chmod +x "$BACKUP_SCRIPT"

# Проверяем существующие cron задачи
echo "📋 Текущие cron задачи:"
crontab -l 2>/dev/null || echo "Cron задачи не найдены"

# Добавляем новую cron задачу
echo ""
echo "➕ Добавление cron задачи для ежедневного резервного копирования в 02:00..."

# Проверяем, есть ли уже такая задача
if crontab -l 2>/dev/null | grep -q "backup-database.sh"; then
    echo "⚠️  Cron задача для резервного копирования уже существует"
else
    # Создаем временный файл с новой cron задачей
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ Cron задача добавлена успешно"
fi

echo ""
echo "📋 Обновленные cron задачи:"
crontab -l

echo ""
echo "✅ Настройка автоматического резервного копирования завершена!"
echo ""
echo "📌 Информация:"
echo "   • Резервные копии создаются ежедневно в 02:00"
echo "   • Логи сохраняются в: /var/log/okdesk_backup.log"
echo "   • Старые копии (>30 дней) удаляются автоматически"
echo ""
echo "🔧 Управление:"
echo "   • Ручное создание резервной копии: ./backup-database.sh"
echo "   • Просмотр логов: tail -f /var/log/okdesk_backup.log"
echo "   • Удаление cron задачи: crontab -e"
echo ""
