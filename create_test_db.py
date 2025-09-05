#!/usr/bin/env python3
"""
Создание новой базы данных для локального тестирования
"""

import sqlite3
import os

# Создаем новую базу данных
db_path = "test_okdesk_bot.db"

# Удаляем старую базу если есть
if os.path.exists(db_path):
    os.remove(db_path)

# Создаем подключение и таблицы
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Создаем таблицу пользователей
cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        telegram_id BIGINT UNIQUE NOT NULL,
        username TEXT,
        user_type TEXT,
        full_name TEXT,
        phone TEXT,
        inn_company TEXT,
        company_id INTEGER,
        company_name TEXT,
        okdesk_contact_id INTEGER,
        contact_auth_code TEXT,
        is_registered BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Создаем таблицу заявок
cursor.execute('''
    CREATE TABLE issues (
        id INTEGER PRIMARY KEY,
        telegram_user_id BIGINT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'new',
        issue_number TEXT,
        okdesk_issue_id INTEGER,
        okdesk_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Создаем таблицу комментариев
cursor.execute('''
    CREATE TABLE comments (
        id INTEGER PRIMARY KEY,
        issue_id INTEGER NOT NULL,
        telegram_user_id BIGINT NOT NULL,
        content TEXT NOT NULL,
        okdesk_comment_id INTEGER,
        is_from_okdesk BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (issue_id) REFERENCES issues (id)
    )
''')

conn.commit()
conn.close()

print(f"✅ База данных создана: {db_path}")
print(f"📁 Размер файла: {os.path.getsize(db_path)} байт")
