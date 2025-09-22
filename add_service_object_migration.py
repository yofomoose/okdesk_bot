#!/usr/bin/env python3
"""
Миграция для добавления поля service_object_name в таблицу users
Запуск: python add_service_object_migration.py
"""

import sys
import os
from sqlalchemy import create_engine, text

# Добавляем путь к проекту для импорта модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config

def add_service_object_column():
    """Добавить колонку service_object_name в таблицу users"""
    try:
        # Создаем движок базы данных
        engine = create_engine(config.DATABASE_URL, echo=True)

        with engine.connect() as conn:
            # Для SQLite проверяем по-другому
            result = conn.execute(text("""
                PRAGMA table_info(users)
            """))

            columns = [row[1] for row in result.fetchall()]  # column[1] - это имя колонки

            if 'service_object_name' in columns:
                print("✅ Колонка service_object_name уже существует")
                return True

            # Добавляем колонку для SQLite
            print("🔄 Добавляем колонку service_object_name...")
            conn.execute(text("""
                ALTER TABLE users ADD COLUMN service_object_name TEXT
            """))

            conn.commit()
            print("✅ Колонка service_object_name успешно добавлена")
            return True

    except Exception as e:
        print(f"❌ Ошибка при добавлении колонки: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Запуск миграции для добавления service_object_name...")
    success = add_service_object_column()
    if success:
        print("✅ Миграция завершена успешно")
    else:
        print("❌ Миграция завершилась с ошибками")
        sys.exit(1)