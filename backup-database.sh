#!/bin/bash

# Скрипт для создания резервной копии базы данных

BACKUP_DIR="/app/data/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="okdesk_bot_backup_${TIMESTAMP}.db"

echo "💾 Создание резервной копии базы данных..."

# Создаем директорию для резервных копий
docker exec okdesk_bot_okdesk_bot_1 mkdir -p $BACKUP_DIR

# Создаем резервную копию
if docker exec okdesk_bot_okdesk_bot_1 test -f /app/data/okdesk_bot.db; then
    docker exec okdesk_bot_okdesk_bot_1 cp /app/data/okdesk_bot.db $BACKUP_DIR/$BACKUP_FILE
    
    echo "✅ Резервная копия создана: $BACKUP_DIR/$BACKUP_FILE"
    
    # Показываем размер файла
    echo "📊 Размер резервной копии:"
    docker exec okdesk_bot_okdesk_bot_1 ls -lh $BACKUP_DIR/$BACKUP_FILE
    
    # Показываем все резервные копии
    echo ""
    echo "📋 Все резервные копии:"
    docker exec okdesk_bot_okdesk_bot_1 ls -lh $BACKUP_DIR/
    
    # Удаляем старые резервные копии (старше 30 дней)
    echo ""
    echo "🧹 Удаление старых резервных копий (старше 30 дней)..."
    docker exec okdesk_bot_okdesk_bot_1 find $BACKUP_DIR -name "okdesk_bot_backup_*.db" -mtime +30 -delete
    
    echo ""
    echo "✅ Резервное копирование завершено!"
    echo "📁 Путь к резервной копии: $BACKUP_DIR/$BACKUP_FILE"
    
else
    echo "❌ Ошибка: база данных не найдена по пути /app/data/okdesk_bot.db"
    exit 1
fi
