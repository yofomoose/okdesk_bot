#!/usr/bin/env python3
"""
Отладка API контактов
"""

import asyncio
import sys
import os
import logging

# Настраиваем логирование
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.okdesk_api import OkdeskAPI

async def debug_contacts_api():
    """Отладка API контактов"""
    
    print("🔧 Отладка API контактов...")
    
    okdesk_api = OkdeskAPI()
    
    try:
        # Прямой запрос к API контактов
        print("📡 Прямой запрос к /contacts...")
        response = await okdesk_api._make_request('GET', '/contacts')
        print(f"   Ответ: {response}")
        
        # Попробуем разные endpoints
        endpoints = [
            '/contacts',
            '/contacts?limit=10',
            '/api/v1/contacts',
        ]
        
        for endpoint in endpoints:
            print(f"\n📡 Пробуем endpoint: {endpoint}")
            try:
                response = await okdesk_api._make_request('GET', endpoint)
                print(f"   Статус: Успех")
                print(f"   Тип ответа: {type(response)}")
                if isinstance(response, dict):
                    print(f"   Ключи: {list(response.keys())}")
                elif isinstance(response, list):
                    print(f"   Количество элементов: {len(response)}")
                print(f"   Данные: {response}")
            except Exception as e:
                print(f"   Ошибка: {e}")
        
    except Exception as e:
        print(f"❌ Общая ошибка: {e}")
        
    finally:
        await okdesk_api.close()

if __name__ == "__main__":
    asyncio.run(debug_contacts_api())
