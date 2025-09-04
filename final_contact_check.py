#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Финальная проверка контактов
"""

import asyncio
from services.okdesk_api import OkdeskAPI

async def main():
    """Тест всех созданных контактов"""
    print("🎯 Финальная проверка созданных контактов")
    
    api = OkdeskAPI()
    
    try:
        print("\n1️⃣ Получаем все контакты...")
        all_contacts = await api.get_contacts(limit=100)
        print(f"Результат: {all_contacts}")
        
        print("\n2️⃣ Поиск по телефону +79999999999...")
        phone_contacts = await api.get_contacts(phone="+79999999999")
        print(f"Результат: {phone_contacts}")
        
        print("\n3️⃣ Поиск контакта ID 23...")
        contact_23 = await api._make_request('GET', '/contacts/23')
        print(f"Контакт 23: {contact_23}")
        
        print("\n4️⃣ Поиск контакта ID 24...")  
        contact_24 = await api._make_request('GET', '/contacts/24')
        print(f"Контакт 24: {contact_24}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await api.close()

if __name__ == "__main__":
    asyncio.run(main())
