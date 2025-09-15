#!/usr/bin/env python3
"""
Скрипт для миграции данных из SQLite в PostgreSQL
Использование: python migrate_to_postgres.py
"""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.database import Base, User, Issue, Comment

# Пути к базам данных
SQLITE_DB_PATH = "okdesk_bot.db"  # Локальный SQLite файл
POSTGRES_URL = os.getenv("DATABASE_URL", "postgresql://okdesk_user:changeme123@localhost:5432/okdesk_bot")

def migrate_data():
    """Миграция данных из SQLite в PostgreSQL"""

    print("🚀 Начинаем миграцию данных из SQLite в PostgreSQL")

    # Проверяем существование SQLite файла
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"❌ SQLite файл {SQLITE_DB_PATH} не найден")
        return False

    # Создаем движки для обеих баз
    sqlite_engine = create_engine(f"sqlite:///{SQLITE_DB_PATH}", echo=False)
    postgres_engine = create_engine(POSTGRES_URL, echo=False)

    # Создаем сессии
    SQLiteSession = sessionmaker(bind=sqlite_engine)
    PostgresSession = sessionmaker(bind=postgres_engine)

    try:
        # Создаем таблицы в PostgreSQL
        print("📊 Создаем таблицы в PostgreSQL...")
        Base.metadata.create_all(bind=postgres_engine, checkfirst=True)

        # Получаем данные из SQLite
        sqlite_session = SQLiteSession()

        print("📖 Читаем данные из SQLite...")

        # Миграция пользователей
        users = sqlite_session.query(User).all()
        print(f"👥 Найдено {len(users)} пользователей")

        postgres_session = PostgresSession()
        for user in users:
            # Проверяем, существует ли уже пользователь
            existing = postgres_session.query(User).filter(User.telegram_id == user.telegram_id).first()
            if not existing:
                postgres_session.merge(user)  # merge для обновления или вставки
            else:
                print(f"⚠️ Пользователь {user.telegram_id} уже существует, пропускаем")

        postgres_session.commit()

        # Миграция заявок
        issues = sqlite_session.query(Issue).all()
        print(f"📋 Найдено {len(issues)} заявок")

        for issue in issues:
            postgres_session.merge(issue)

        postgres_session.commit()

        # Миграция комментариев
        comments = sqlite_session.query(Comment).all()
        print(f"💬 Найдено {len(comments)} комментариев")

        for comment in comments:
            postgres_session.merge(comment)

        postgres_session.commit()

        sqlite_session.close()
        postgres_session.close()

        print("✅ Миграция завершена успешно!")
        return True

    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        return False

if __name__ == "__main__":
    success = migrate_data()
    sys.exit(0 if success else 1)