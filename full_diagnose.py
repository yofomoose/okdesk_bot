#!/usr/bin/env python3
"""
Диагностический скрипт для OKDesk Bot
Проверяет состояние базы данных, API, конфигурации и webhook
"""

import os
import sqlite3
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Добавляем текущую директорию в путь для импорта модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config import DATABASE_URL, BOT_TOKEN, OKDESK_API_URL, OKDESK_API_TOKEN
    from services.okdesk_api import OkdeskAPI
    from database.models import Issue, User, Comment
    from services.issue_service import IssueService
    from services.user_service import UserService
    from services.comment_service import CommentService
    import requests
except ImportError as e:
    print(f"❌ Ошибка импорта модулей: {e}")
    print("Убедитесь, что скрипт запускается из корневой директории проекта")
    sys.exit(1)

def print_header(title):
    """Печать заголовка секции"""
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")

def print_status(message, status):
    """Печать статуса (✅ или ❌)"""
    icon = "✅" if status else "❌"
    print(f"{icon} {message}")

def check_config():
    """Проверка конфигурации"""
    print_header("ПРОВЕРКА КОНФИГУРАЦИИ")
    
    # Проверяем обязательные переменные
    config_vars = {
        'BOT_TOKEN': BOT_TOKEN,
        'OKDESK_API_URL': OKDESK_API_URL,
        'OKDESK_API_TOKEN': OKDESK_API_TOKEN,
        'DATABASE_URL': DATABASE_URL
    }
    
    all_ok = True
    for var_name, var_value in config_vars.items():
        if var_value:
            print_status(f"{var_name}: {'*' * 10}", True)
        else:
            print_status(f"{var_name}: не установлен", False)
            all_ok = False
    
    # Проверяем файл .env
    env_exists = os.path.exists('.env')
    print_status(f"Файл .env существует", env_exists)
    
    return all_ok and env_exists

def check_database():
    """Проверка базы данных"""
    print_header("ПРОВЕРКА БАЗЫ ДАННЫХ")
    
    try:
        # Парсим URL базы данных
        if DATABASE_URL.startswith('sqlite:///'):
            db_path = DATABASE_URL.replace('sqlite:///', '')
        elif DATABASE_URL.startswith('sqlite:////'):
            db_path = DATABASE_URL.replace('sqlite:////', '/')
        else:
            print_status(f"Неподдерживаемый тип БД: {DATABASE_URL}", False)
            return False
        
        print(f"📍 Путь к базе данных: {db_path}")
        
        # Проверяем существование файла
        db_exists = os.path.exists(db_path)
        print_status(f"Файл базы данных существует", db_exists)
        
        if not db_exists:
            return False
        
        # Подключаемся и проверяем таблицы
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Получаем список таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [table[0] for table in cursor.fetchall()]
        
        expected_tables = ['users', 'issues', 'comments']
        for table in expected_tables:
            table_exists = table in tables
            print_status(f"Таблица '{table}' существует", table_exists)
        
        # Подсчитываем записи
        for table in expected_tables:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"📊 Записей в таблице '{table}': {count}")
        
        # Проверяем размер файла
        file_size = os.path.getsize(db_path)
        print(f"📏 Размер файла базы данных: {file_size} байт ({file_size / 1024:.1f} KB)")
        
        # Проверяем последнее изменение
        mod_time = datetime.fromtimestamp(os.path.getmtime(db_path))
        print(f"⏰ Последнее изменение: {mod_time}")
        
        conn.close()
        return True
        
    except Exception as e:
        print_status(f"Ошибка проверки базы данных: {e}", False)
        return False

async def check_api():
    """Проверка Okdesk API"""
    print_header("ПРОВЕРКА OKDESK API")
    
    try:
        okdesk_api = OkdeskAPI()
        
        # Тестируем соединение
        connection_ok = await okdesk_api.test_connection()
        print_status("Соединение с Okdesk API", connection_ok)
        
        if connection_ok:
            # Получаем информацию о текущем пользователе
            try:
                user_info = await okdesk_api.get_current_user()
                if user_info:
                    print(f"👤 API пользователь: {user_info.get('name', 'Неизвестен')}")
                    print(f"📧 Email: {user_info.get('email', 'Не указан')}")
                
                # Проверяем доступ к заявкам
                issues = await okdesk_api.get_issues(limit=1)
                print_status(f"Доступ к заявкам (найдено: {len(issues)})", len(issues) >= 0)
                
                # Проверяем доступ к контактам
                contacts = await okdesk_api.get_contacts(limit=1)
                print_status(f"Доступ к контактам (найдено: {len(contacts)})", len(contacts) >= 0)
                
            except Exception as e:
                print_status(f"Ошибка получения данных API: {e}", False)
        
        await okdesk_api.close()
        return connection_ok
        
    except Exception as e:
        print_status(f"Ошибка проверки API: {e}", False)
        return False

def check_webhook():
    """Проверка webhook"""
    print_header("ПРОВЕРКА WEBHOOK")
    
    try:
        # Проверяем доступность webhook на localhost:8000
        webhook_url = "http://localhost:8000/okdesk-webhook"
        
        try:
            response = requests.get(webhook_url, timeout=5)
            # Webhook должен вернуть 405 (Method Not Allowed) для GET запроса
            webhook_ok = response.status_code == 405
            print_status(f"Webhook доступен на {webhook_url}", webhook_ok)
            print(f"📡 HTTP статус: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print_status("Webhook недоступен (сервер не запущен)", False)
            return False
        except Exception as e:
            print_status(f"Ошибка проверки webhook: {e}", False)
            return False
        
        return webhook_ok
        
    except Exception as e:
        print_status(f"Ошибка проверки webhook: {e}", False)
        return False

def check_docker():
    """Проверка Docker контейнеров"""
    print_header("ПРОВЕРКА DOCKER КОНТЕЙНЕРОВ")
    
    try:
        import subprocess
        
        # Проверяем запущенные контейнеры
        result = subprocess.run(['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            okdesk_containers = [line for line in lines if 'okdesk' in line.lower()]
            
            print(f"🐳 Найдено OKDesk контейнеров: {len(okdesk_containers) - 1 if len(okdesk_containers) > 1 else 0}")  # -1 для заголовка
            
            for container in okdesk_containers[1:]:  # Пропускаем заголовок
                name, status = container.split('\t')
                is_running = 'Up' in status
                print_status(f"Контейнер {name}: {status}", is_running)
            
            return len(okdesk_containers) > 1
        else:
            print_status("Docker недоступен", False)
            return False
            
    except Exception as e:
        print_status(f"Ошибка проверки Docker: {e}", False)
        return False

async def check_database_services():
    """Проверка работы сервисов базы данных"""
    print_header("ПРОВЕРКА СЕРВИСОВ БАЗЫ ДАННЫХ")
    
    try:
        # Проверяем UserService
        users = UserService.get_all_users()
        print_status(f"UserService работает (пользователей: {len(users)})", True)
        
        # Проверяем IssueService
        issues = IssueService.get_all_issues()
        print_status(f"IssueService работает (заявок: {len(issues)})", True)
        
        # Проверяем CommentService
        # Получаем комментарии для первой заявки если есть
        if issues:
            comments = CommentService.get_issue_comments(issues[0].id)
            print_status(f"CommentService работает (комментариев к первой заявке: {len(comments)})", True)
        else:
            print_status("CommentService недоступен для проверки (нет заявок)", True)
        
        return True
        
    except Exception as e:
        print_status(f"Ошибка проверки сервисов: {e}", False)
        return False

def main():
    """Основная функция диагностики"""
    print("🔍 ДИАГНОСТИКА СИСТЕМЫ OKDESK BOT")
    print(f"⏰ Время запуска: {datetime.now()}")
    
    # Запускаем все проверки
    results = {}
    
    results['config'] = check_config()
    results['database'] = check_database()
    results['docker'] = check_docker()
    results['webhook'] = check_webhook()
    
    # Асинхронные проверки
    async def async_checks():
        results['api'] = await check_api()
        results['db_services'] = await check_database_services()
    
    asyncio.run(async_checks())
    
    # Финальный отчет
    print_header("ИТОГОВЫЙ ОТЧЕТ")
    
    total_checks = len(results)
    passed_checks = sum(1 for result in results.values() if result)
    
    for check_name, result in results.items():
        print_status(f"{check_name.upper()}", result)
    
    print(f"\n📊 Пройдено проверок: {passed_checks}/{total_checks}")
    
    if passed_checks == total_checks:
        print("\n🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! Система работает корректно.")
    elif passed_checks >= total_checks * 0.8:
        print("\n⚠️  БОЛЬШИНСТВО ПРОВЕРОК ПРОЙДЕНО. Есть незначительные проблемы.")
    else:
        print("\n❌ ОБНАРУЖЕНЫ СЕРЬЕЗНЫЕ ПРОБЛЕМЫ. Требуется вмешательство.")
    
    # Рекомендации
    print_header("РЕКОМЕНДАЦИИ")
    
    if not results.get('config'):
        print("• Проверьте файл .env и убедитесь, что все переменные установлены")
    
    if not results.get('database'):
        print("• Проверьте путь к базе данных и права доступа")
    
    if not results.get('docker'):
        print("• Запустите контейнеры: make start")
    
    if not results.get('api'):
        print("• Проверьте токен Okdesk API и доступность сервиса")
    
    if not results.get('webhook'):
        print("• Убедитесь, что webhook сервер запущен на порту 8000")
    
    return passed_checks == total_checks

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Диагностика прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Критическая ошибка диагностики: {e}")
        sys.exit(1)
