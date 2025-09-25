#!/usr/bin/env python3
"""
Скрипт миграции базы данных для добавления поля rating_requested в таблицу issues
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

        # Добавляем поле rating_requested, если его нет
        if 'rating_requested' not in column_names:
            print("➕ Добавление поля rating_requested...")
            cursor.execute("ALTER TABLE issues ADD COLUMN rating_requested BOOLEAN DEFAULT 0")
            print("✅ Поле rating_requested добавлено")
        else:
            print("ℹ️  Поле rating_requested уже существует")

        # Сохраняем изменения
        conn.commit()
        print("✅ Миграция завершена успешно")

        # Выводим обновленную структуру таблицы
        cursor.execute("PRAGMA table_info(issues)")
        columns = cursor.fetchall()
        print("📋 Обновленная структура таблицы issues:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")

        return True

    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🚀 Начинаем миграцию базы данных...")
    success = migrate_database()
    if success:
        print("✅ Миграция завершена успешно")
    else:
        print("❌ Миграция завершилась с ошибками")