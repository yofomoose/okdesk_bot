#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для установки персонального токена портала для пользователя
Использование: python set_user_portal_token.py <telegram_id> <portal_token>
"""

import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from database.crud import UserService

def set_user_portal_token(telegram_id: int, portal_token: str):
    """Установить токен портала для пользователя"""
    try:
        user = UserService.update_portal_token_by_telegram_id(telegram_id, portal_token)
        if user:
            print(f"✅ Токен портала успешно установлен для пользователя {telegram_id}")
            print(f"👤 Пользователь: {user.full_name or user.username or 'N/A'}")
            print(f"🔑 Токен: {portal_token}")
        else:
            print(f"❌ Пользователь с Telegram ID {telegram_id} не найден")
    except Exception as e:
        print(f"❌ Ошибка при установке токена: {e}")

def main():
    if len(sys.argv) != 3:
        print("Использование: python set_user_portal_token.py <telegram_id> <portal_token>")
        print("Пример: python set_user_portal_token.py 123456789 7812-5733-8392-7092")
        sys.exit(1)

    try:
        telegram_id = int(sys.argv[1])
        portal_token = sys.argv[2]

        print(f"🔄 Установка токена портала для пользователя {telegram_id}...")
        set_user_portal_token(telegram_id, portal_token)

    except ValueError:
        print("❌ Telegram ID должен быть числом")
        sys.exit(1)

if __name__ == "__main__":
    main()