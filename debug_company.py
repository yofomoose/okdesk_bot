#!/usr/bin/env python3

import asyncio
import sys
import os

# Добавляем путь к корневой директории проекта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.okdesk_api import OkdeskAPI

async def debug_company_creation():
    """Отладка создания компании"""
    
    api = OkdeskAPI()
    
    try:
        print("=== ОТЛАДКА СОЗДАНИЯ КОМПАНИИ ===")
        
        # Тестируем разные варианты данных
        variants = [
            {
                'name': 'Тест Компания 1',
                'inn_company': '5501183308'
            },
            {
                'name': 'Тест Компания 2', 
                'inn_company': '5501183308',
                'address': 'Тестовый адрес'
            },
            {
                'name': 'Тест Компания 3',
                'inn_company': '5501183308',
                'phone': '+7(495)123-45-67',
                'email': 'test@company.ru'
            }
        ]
        
        for i, data in enumerate(variants):
            print(f"\n{i+1}. Тестируем вариант: {data}")
            
            response = await api._make_request('POST', '/companies', data)
            print(f"   Ответ: {response}")
            
            if response and 'id' in response:
                print(f"   ✅ Компания создана: {response.get('id')}")
                break
            else:
                print(f"   ❌ Ошибка создания")
        
        # Также попробуем получить схему API
        print(f"\n4. Пробуем получить информацию о параметрах...")
        schema_response = await api._make_request('GET', '/companies', {})
        print(f"   Схема компаний: {schema_response}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await api.close()

if __name__ == "__main__":
    asyncio.run(debug_company_creation())
