#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Миграция: добавление поля portal_token в таблицу users
"""

import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from models.database import engine, Base
from sqlalchemy import text

def add_portal_token_column():
    """Добавляет колонку portal_token в таблицу users"""
    try:
        # Проверяем, существует ли уже колонка
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'portal_token'
            """))

            if result.fetchone():
                print("✅ Колонка portal_token уже существует")
                return

            # Добавляем колонку
            print("🔄 Добавляю колонку portal_token...")
            conn.execute(text("""
                ALTER TABLE users ADD COLUMN portal_token VARCHAR(255)
            """))
            conn.commit()

        print("✅ Колонка portal_token успешно добавлена")

    except Exception as e:
        print(f"❌ Ошибка при добавлении колонки: {e}")

        # Для SQLite используем другой подход
        try:
            print("🔄 Пробую альтернативный метод для SQLite...")
            with engine.connect() as conn:
                # Создаем новую таблицу с новой колонкой
                conn.execute(text("""
                    CREATE TABLE users_new (
                        id INTEGER PRIMARY KEY,
                        telegram_id BIGINT UNIQUE,
                        username VARCHAR(255),
                        user_type VARCHAR(50) NOT NULL,
                        full_name VARCHAR(255),
                        phone VARCHAR(255),
                        contact_auth_code VARCHAR(255),
                        okdesk_contact_id INTEGER,
                        portal_token VARCHAR(255),
                        inn_company VARCHAR(255),
                        company_id INTEGER,
                        company_name VARCHAR(255),
                        is_registered BOOLEAN DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """))

                # Копируем данные
                conn.execute(text("""
                    INSERT INTO users_new (
                        id, telegram_id, username, user_type, full_name, phone,
                        contact_auth_code, okdesk_contact_id, inn_company,
                        company_id, company_name, is_registered, created_at, updated_at
                    )
                    SELECT id, telegram_id, username, user_type, full_name, phone,
                           contact_auth_code, okdesk_contact_id, inn_company,
                           company_id, company_name, is_registered, created_at, updated_at
                    FROM users
                """))

                # Удаляем старую таблицу и переименовываем новую
                conn.execute(text("DROP TABLE users"))
                conn.execute(text("ALTER TABLE users_new RENAME TO users"))

                conn.commit()

            print("✅ Миграция SQLite завершена успешно")

        except Exception as e2:
            print(f"❌ Ошибка миграции SQLite: {e2}")

if __name__ == "__main__":
    print("🔄 Начинаю миграцию: добавление portal_token...")
    add_portal_token_column()
    print("✅ Миграция завершена")