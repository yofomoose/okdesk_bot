#!/usr/bin/env python3

import asyncio
import sys
import os

# Добавляем путь к корневой директории проекта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.okdesk_api import OkdeskAPI

async def get_roles():
    """Получить список ролей"""
    
    api = OkdeskAPI()
    
    try:
        print("=== ПОЛУЧЕНИЕ СПИСКА РОЛЕЙ ===")
        
        roles_response = await api._make_request('GET', '/employee_roles', {})
        print(f"Роли: {roles_response}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await api.close()

if __name__ == "__main__":
    asyncio.run(get_roles())
