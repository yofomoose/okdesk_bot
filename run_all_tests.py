#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
import os
import logging
import time
from datetime import datetime
import argparse
import importlib

# Добавляем путь к корневой директории проекта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                   format='%(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

# Список тестов для запуска
TESTS = [
    "test_client_binding_fixed",
    "test_comment_with_author",
    "quick_check_fixes"
]

# Дополнительные диагностические инструменты
DIAGNOSTIC_TOOLS = [
    "full_workflow_diagnosis",
    "fix_verification_report"
]

async def run_tests(tests, verbose=False):
    """
    Запускает указанные тесты
    
    Args:
        tests: список имен модулей с тестами
        verbose: включить подробное логирование
    """
    
    results = {}
    
    logger.info(f"🚀 Запуск {len(tests)} тестов")
    
    start_time = time.time()
    
    for test_name in tests:
        logger.info(f"\n📋 Запуск теста: {test_name}")
        
        try:
            # Импортируем модуль с тестом
            test_module = importlib.import_module(test_name)
            
            # Находим основную функцию
            if hasattr(test_module, 'main'):
                test_func = test_module.main
            else:
                # Предполагаем, что основная функция имеет то же имя, что и модуль
                test_func_name = test_name
                if test_func_name.startswith("test_"):
                    test_func_name = test_func_name[5:]
                
                test_func = getattr(test_module, test_func_name)
            
            # Если verbose включен, установим более подробное логирование
            if verbose:
                logging.getLogger('services.okdesk_api').setLevel(logging.DEBUG)
            else:
                # Временно уменьшаем уровень логирования для запуска теста
                original_level = logger.level
                logger.setLevel(logging.WARNING)
                for handler in logging.root.handlers:
                    handler.setLevel(logging.WARNING)
                
            # Запускаем тест
            test_start_time = time.time()
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
                
            # Восстанавливаем уровень логирования
            if not verbose:
                logger.setLevel(original_level)
                for handler in logging.root.handlers:
                    handler.setLevel(original_level)
                
            test_end_time = time.time()
            test_duration = test_end_time - test_start_time
            
            # Сохраняем результат
            if isinstance(result, bool):
                success = result
                details = None
            elif isinstance(result, dict):
                success = result.get('success', False)
                details = result
            else:
                success = bool(result)
                details = None
                
            results[test_name] = {
                "success": success,
                "duration": test_duration,
                "details": details
            }
            
            # Выводим результат
            if success:
                logger.info(f"✅ Тест {test_name} пройден успешно ({test_duration:.2f} сек)")
            else:
                logger.error(f"❌ Тест {test_name} не пройден ({test_duration:.2f} сек)")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при запуске теста {test_name}: {e}")
            import traceback
            traceback.print_exc()
            
            results[test_name] = {
                "success": False,
                "error": str(e),
                "duration": 0
            }
    
    # Выводим общий результат
    end_time = time.time()
    total_duration = end_time - start_time
    
    success_count = sum(1 for result in results.values() if result["success"])
    fail_count = len(results) - success_count
    
    logger.info(f"\n🏁 ИТОГИ ТЕСТИРОВАНИЯ:")
    logger.info(f"   Всего тестов: {len(results)}")
    logger.info(f"   Успешных: {success_count}")
    logger.info(f"   Неудачных: {fail_count}")
    logger.info(f"   Общее время: {total_duration:.2f} секунд")
    
    # Подробные результаты по каждому тесту
    logger.info(f"\n📊 РЕЗУЛЬТАТЫ ТЕСТОВ:")
    for test_name, result in results.items():
        status = "✅" if result["success"] else "❌"
        logger.info(f"   {status} {test_name}: {result['duration']:.2f} сек")
        if not result["success"] and "error" in result:
            logger.info(f"      Ошибка: {result['error']}")
    
    return {
        "success": fail_count == 0,
        "tests": results,
        "total_tests": len(results),
        "success_count": success_count,
        "fail_count": fail_count,
        "duration": total_duration
    }

async def main():
    """Главная функция"""
    
    parser = argparse.ArgumentParser(description='Запуск тестов для проверки исправлений бота Okdesk')
    parser.add_argument('--all', action='store_true', help='Запустить все тесты и диагностические инструменты')
    parser.add_argument('--diagnostic', action='store_true', help='Запустить только диагностические инструменты')
    parser.add_argument('--verbose', action='store_true', help='Включить подробное логирование')
    parser.add_argument('--tests', nargs='+', help='Список тестов для запуска')
    
    args = parser.parse_args()
    
    # Определяем какие тесты запускать
    tests_to_run = []
    
    if args.tests:
        tests_to_run = args.tests
    elif args.diagnostic:
        tests_to_run = DIAGNOSTIC_TOOLS
    elif args.all:
        tests_to_run = TESTS + DIAGNOSTIC_TOOLS
    else:
        tests_to_run = TESTS
    
    # Запускаем тесты
    await run_tests(tests_to_run, args.verbose)

if __name__ == "__main__":
    asyncio.run(main())
