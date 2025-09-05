#!/usr/bin/env python3

import asyncio
import sys
import os

# Добавляем путь к корневой директории проекта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.okdesk_api import OkdeskAPI

async def debug_company_api():
    """Отладка API компаний"""
    
    api = OkdeskAPI()
    
    try:
        print("=== ОТЛАДКА API КОМПАНИЙ ===")
        
        # Разные варианты запросов
        endpoints = [
            '/companies',
            '/companies?page=1', 
            '/companies?limit=10',
            '/companies?all=1',
            '/companies/1',  # Попробуем получить компанию по ID=1
            '/companies/search?name=A1',
            '/companies/search?inn=5501183308'
        ]
        
        for endpoint in endpoints:
            print(f"\n🔍 Тестируем: {endpoint}")
            try:
                response = await api._make_request('GET', endpoint, {})
                
                if response:
                    print(f"   ✅ Ответ: {str(response)[:200]}...")
                    
                    # Если нашли компании, ищем нашу
                    if isinstance(response, dict):
                        if 'companies' in response and response['companies']:
                            companies = response['companies']
                            print(f"   📊 Найдено компаний: {len(companies)}")
                            
                            # Ищем A1, ООО
                            for company in companies:
                                if company.get('inn_company') == '5501183308':
                                    print(f"   🎯 НАЙДЕНА A1, ООО: {company}")
                                    return company
                        elif 'id' in response:  # Одна компания
                            if response.get('inn_company') == '5501183308':
                                print(f"   🎯 НАЙДЕНА A1, ООО: {response}")
                                return response
                else:
                    print(f"   ❌ Пустой ответ")
                    
            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
        
        print(f"\n🤔 Возможные причины:")
        print(f"• API требует специальные права для просмотра компаний")
        print(f"• Компании доступны только через другие endpoints") 
        print(f"• Нужна пагинация или фильтры")
        
    except Exception as e:
        print(f"❌ Общая ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await api.close()

if __name__ == "__main__":
    asyncio.run(debug_company_api())
