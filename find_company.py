#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
import sys
import json
import logging

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.okdesk_api import OkdeskAPI

# Настраиваем логирование
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_find_company_by_inn():
    """Тестовая функция для поиска компании по ИНН"""
    api = OkdeskAPI()
    
    try:
        # Получаем ИНН из командной строки или запрашиваем у пользователя
        if len(sys.argv) > 1:
            inn = sys.argv[1]
        else:
            inn = input("Введите ИНН для поиска: ")
        
        print(f"\n🔍 Поиск компании с ИНН: {inn}")
        
        # Выполняем поиск
        company = await api.find_company_by_inn(inn, create_if_not_found=False)
        
        if company:
            print(f"\n✅ Компания найдена!")
            print(f"ID: {company.get('id')}")
            print(f"Название: {company.get('name')}")
            
            # Проверяем, где хранится ИНН
            print("\nДанные ИНН:")
            print(f"inn: {company.get('inn', 'Не найдено')}")
            print(f"inn_company: {company.get('inn_company', 'Не найдено')}")
            print(f"legal_inn: {company.get('legal_inn', 'Не найдено')}")
            
            # Проверяем параметры
            if 'parameters' in company:
                print("\nПараметры:")
                for param in company.get('parameters', []):
                    print(f"{param.get('code', 'Без кода')}: {param.get('value', 'Без значения')}")
            
            # Проверяем custom_parameters
            if 'custom_parameters' in company:
                print("\nПользовательские параметры:")
                for key, value in company.get('custom_parameters', {}).items():
                    print(f"{key}: {value}")
            
            # Опционально показываем все данные
            show_all = input("\nПоказать все данные компании? (y/n): ").lower() == 'y'
            if show_all:
                print("\nВсе данные компании:")
                print(json.dumps(company, ensure_ascii=False, indent=2))
        else:
            print(f"\n❌ Компания с ИНН {inn} не найдена")
            
            # Опционально создаем компанию
            create = input("\nСоздать новую компанию с этим ИНН? (y/n): ").lower() == 'y'
            if create:
                name = input("Введите название компании: ")
                
                print(f"\nСоздаю компанию '{name}' с ИНН {inn}...")
                new_company = await api.create_company(
                    name=name,
                    inn=inn,
                    comment=f"Компания создана автоматически с ИНН {inn}"
                )
                
                if new_company and 'id' in new_company:
                    print(f"\n✅ Компания успешно создана!")
                    print(f"ID: {new_company.get('id')}")
                    print(f"Название: {new_company.get('name')}")
                else:
                    print(f"\n❌ Не удалось создать компанию")
    
    finally:
        await api.close()

async def main():
    """Основная функция"""
    await test_find_company_by_inn()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nОперация прервана пользователем")
    except Exception as e:
        print(f"\n❌ Произошла ошибка: {e}")
        import traceback
        traceback.print_exc()
