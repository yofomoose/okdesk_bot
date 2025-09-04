#!/usr/bin/env python3
"""
Скрипт для проверки и исправления состояния пользователей в базе данных
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.crud import UserService
from models.database import create_tables

def check_user_registration():
    """Проверяет состояние регистрации всех пользователей"""
    
    print("🔍 ПРОВЕРКА РЕГИСТРАЦИИ ПОЛЬЗОВАТЕЛЕЙ")
    print("=" * 50)
    
    users = UserService.get_all_users()
    print(f"👥 Всего пользователей в базе: {len(users)}")
    
    if not users:
        print("❌ Пользователи не найдены")
        return
    
    for user in users:
        print(f"\n👤 Пользователь ID {user.telegram_id}:")
        print(f"   Username: @{user.username if user.username else 'не указан'}")
        print(f"   Тип: {user.user_type}")
        print(f"   Зарегистрирован: {'✅' if user.is_registered else '❌'}")
        
        if user.user_type == "physical":
            print(f"   ФИО: {user.full_name or 'не указано'}")
            print(f"   Телефон: {user.phone or 'не указан'}")
        elif user.user_type == "legal":
            print(f"   ИНН: {user.inn_company or 'не указан'}")
            print(f"   Компания: {user.company_name or 'не указана'}")
        
        # Проверяем, должен ли быть пользователь зарегистрирован
        should_be_registered = False
        if user.user_type == "physical" and user.full_name and user.phone:
            should_be_registered = True
        elif user.user_type == "legal" and user.inn_company:
            should_be_registered = True
        
        if should_be_registered and not user.is_registered:
            print(f"   ⚠️ ПРОБЛЕМА: Пользователь должен быть зарегистрирован, но флаг is_registered = False")

def fix_user_registration(telegram_id: int):
    """Исправляет регистрацию конкретного пользователя"""
    
    print(f"🔧 ИСПРАВЛЕНИЕ РЕГИСТРАЦИИ ДЛЯ ПОЛЬЗОВАТЕЛЯ {telegram_id}")
    print("=" * 50)
    
    user = UserService.get_user_by_telegram_id(telegram_id)
    if not user:
        print("❌ Пользователь не найден")
        return
    
    print(f"👤 Найден пользователь:")
    print(f"   Username: @{user.username if user.username else 'не указан'}")
    print(f"   Тип: {user.user_type}")
    print(f"   Зарегистрирован: {'✅' if user.is_registered else '❌'}")
    
    # Проверяем данные для регистрации
    if user.user_type == "physical":
        if user.full_name and user.phone:
            # Обновляем пользователя (это установит is_registered = True)
            updated_user = UserService.update_user_physical(
                user.id, user.full_name, user.phone
            )
            if updated_user and updated_user.is_registered:
                print("✅ Регистрация исправлена для физического лица")
            else:
                print("❌ Ошибка при исправлении регистрации")
        else:
            print("❌ Недостаточно данных для физического лица (нет имени или телефона)")
    
    elif user.user_type == "legal":
        if user.inn_company:
            # Обновляем пользователя (это установит is_registered = True)
            updated_user = UserService.update_user_legal(
                user.id, user.inn_company, user.company_id, user.company_name
            )
            if updated_user and updated_user.is_registered:
                print("✅ Регистрация исправлена для юридического лица")
            else:
                print("❌ Ошибка при исправлении регистрации")
        else:
            print("❌ Недостаточно данных для юридического лица (нет ИНН)")
    else:
        print("❌ Неизвестный тип пользователя")

def main():
    """Основная функция"""
    
    # Инициализируем базу данных
    create_tables()
    
    if len(sys.argv) > 1:
        try:
            telegram_id = int(sys.argv[1])
            fix_user_registration(telegram_id)
        except ValueError:
            print("❌ Неверный формат Telegram ID")
            print("Использование: python fix_registration.py [TELEGRAM_ID]")
    else:
        check_user_registration()
        
        print("\n" + "=" * 50)
        print("💡 СПРАВКА:")
        print("Для исправления регистрации конкретного пользователя:")
        print("python fix_registration.py TELEGRAM_ID")
        print("\nНапример: python fix_registration.py 7250839414")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Операция прервана пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
