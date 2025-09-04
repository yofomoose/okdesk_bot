#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Создание тестовой заявки для проверки комментариев
"""

import asyncio
from services.okdesk_api import OkdeskAPI

async def main():
    """Создание тестовой заявки"""
    print("🎯 Создаем тестовую заявку для проверки комментариев")
    
    api = OkdeskAPI()
    
    try:
        # Найдем созданный контакт Васи
        print("\n1️⃣ Ищем контакт Васи...")
        contacts = await api.get_contacts(phone="+79999999999")
        
        if not contacts:
            print("❌ Контакт не найден")
            return
            
        contact = contacts[0]
        print(f"✅ Найден контакт: {contact['first_name']} {contact['last_name']} (ID: {contact['id']})")
        
        # Создаем тестовую заявку
        print("\n2️⃣ Создаем тестовую заявку...")
        issue_data = {
            'title': 'Тестовая заявка для проверки webhook комментариев',
            'description': 'Эта заявка создана для тестирования системы уведомлений о комментариях через webhook.',
            'contact_id': contact['id']
        }
        
        issue = await api.create_issue(**issue_data)
        
        if issue and 'id' in issue:
            print(f"✅ Заявка создана успешно!")
            print(f"   🎫 ID заявки: {issue['id']}")
            print(f"   📝 Название: {issue.get('title', 'Не указано')}")
            print(f"   👤 Контакт: {contact['first_name']} {contact['last_name']}")
            
            print(f"\n🔗 Теперь вы можете:")
            print(f"   1. Зайти в Okdesk")
            print(f"   2. Найти заявку #{issue['id']}")
            print(f"   3. Добавить к ней комментарий")
            print(f"   4. Webhook сервер должен получить уведомление!")
            
        else:
            print("❌ Не удалось создать заявку")
            print(f"Ответ API: {issue}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await api.close()

if __name__ == "__main__":
    asyncio.run(main())
