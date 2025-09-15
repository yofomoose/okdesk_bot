#!/usr/bin/env python3
"""
Скрипт миграции базы данных для добавления полей rating и rating_comment в таблицу issues
"""

import sqlite3
import os
from pathlib import Path

def migrate_database():
    """Миграция базы данных"""

    # Определяем путь к базе данных
    if os.path.exists("/app/data"):
        # Запущено в Docker контейнере
        db_path = "/app/data/okdesk_bot.db"
    else:
        # Локальный запуск
        db_path = "data/okdesk_bot.db"

    if not os.path.exists(db_path):
        print(f"❌ База данных не найдена: {db_path}")
        return False

    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Проверяем, существуют ли уже новые поля
        cursor.execute("PRAGMA table_info(issues)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        print(f"📋 Текущие поля таблицы issues: {column_names}")

        # Добавляем поле rating, если его нет
        if 'rating' not in column_names:
            print("➕ Добавление поля rating...")
            cursor.execute("ALTER TABLE issues ADD COLUMN rating INTEGER")
            print("✅ Поле rating добавлено")
        else:
            print("ℹ️  Поле rating уже существует")

        # Добавляем поле rating_comment, если его нет
        if 'rating_comment' not in column_names:
            print("➕ Добавление поля rating_comment...")
            cursor.execute("ALTER TABLE issues ADD COLUMN rating_comment TEXT")
            print("✅ Поле rating_comment добавлено")
        else:
            print("ℹ️  Поле rating_comment уже существует")

        # Сохраняем изменения
        conn.commit()

        # Проверяем результат
        cursor.execute("PRAGMA table_info(issues)")
        updated_columns = cursor.fetchall()
        updated_column_names = [col[1] for col in updated_columns]

        print(f"📋 Обновленные поля таблицы issues: {updated_column_names}")

        # Закрываем соединение
        conn.close()

        print("✅ Миграция завершена успешно!")
        return True

    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        return False

if __name__ == "__main__":
    print("🔄 Запуск миграции базы данных...")
    success = migrate_database()
    if success:
        print("🎉 Миграция завершена!")
    else:
        print("💥 Миграция не удалась!")
        exit(1)