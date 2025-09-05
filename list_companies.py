#!/usr/bin/env python3

import asyncio
import sys
import os

# Добавляем путь к корневой директории проекта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.okdesk_api import OkdeskAPI

async def list_existing_companies():
    """Получить список существующих компаний"""
    
    api = OkdeskAPI()
    
    try:
        print("=== СПИСОК СУЩЕСТВУЮЩИХ КОМПАНИЙ ===")
        
        # Пробуем разные способы получить список компаний
        endpoints = [
            '/companies',
            '/companies/list',  
            '/company'
        ]
        
        for endpoint in endpoints:
            print(f"\n📡 Пробуем {endpoint}...")
            response = await api._make_request('GET', endpoint, {})
            print(f"Ответ: {response}")
            
            if response:
                break
                
        # Также попробуем поиск по пустому запросу
        print(f"\n🔍 Пробуем поиск по пустому запросу...")
        search_response = await api._make_request('GET', '/companies/search', {})
        print(f"Поиск: {search_response}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await api.close()

if __name__ == "__main__":
    asyncio.run(list_existing_companies())
