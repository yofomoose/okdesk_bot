#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Простая миграция: добавление поля portal_token с помощью SQLAlchemy
"""

import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy import Column, String, text
from models.database import engine, Base

def add_portal_token_column():
    """Добавляет колонку portal_token в таблицу users"""
    try:
        # Проверяем, существует ли уже колонка
        with engine.connect() as conn:
            try:
                result = conn.execute(text("PRAGMA table_info(users)"))
                columns = [row[1] for row in result.fetchall()]

                if 'portal_token' in columns:
                    print("✅ Колонка portal_token уже существует")
                    return

                # Добавляем колонку для SQLite
                conn.execute(text("ALTER TABLE users ADD COLUMN portal_token VARCHAR(255)"))
                conn.commit()

                print("✅ Колонка portal_token успешно добавлена")

            except Exception as e:
                print(f"❌ Ошибка при работе с SQLite: {e}")

    except Exception as e:
        print(f"❌ Ошибка при добавлении колонки: {e}")

if __name__ == "__main__":
    print("🔄 Начинаю простую миграцию: добавление portal_token...")
    add_portal_token_column()
    print("✅ Миграция завершена")