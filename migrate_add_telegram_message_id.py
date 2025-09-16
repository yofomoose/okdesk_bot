#!/usr/bin/env python3
"""
Миграция базы данных: добавление поля telegram_message_id в таблицу issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
import config

def migrate_database():
    """Добавляет поле telegram_message_id в таблицу issues"""
    try:
        engine = create_engine(config.DATABASE_URL, echo=True)

        with engine.connect() as conn:
            # Проверяем, существует ли уже колонка
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'issues' AND column_name = 'telegram_message_id'
            """))

            if result.fetchone():
                print("✅ Колонка telegram_message_id уже существует")
                return True

            # Добавляем колонку
            conn.execute(text("""
                ALTER TABLE issues ADD COLUMN telegram_message_id INTEGER
            """))

            conn.commit()
            print("✅ Колонка telegram_message_id успешно добавлена в таблицу issues")
            return True

    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        return False

if __name__ == "__main__":
    success = migrate_database()
    sys.exit(0 if success else 1)