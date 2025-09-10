#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
import os
import logging
import time
from datetime import datetime
import argparse

# Добавляем путь к корневой директории проекта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.okdesk_api import OkdeskAPI

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                   format='%(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

async def quick_check_fixes():
    """
    Быстрая проверка работы исправлений.
    Создает тестовый контакт, заявку, комментарий и проверяет корректность привязок.
    """
    
    logger.info("🔍 Быстрая проверка работы исправлений")
    
    # Создаем экземпляр API клиента
    api = OkdeskAPI()
    
    try:
        timestamp = int(time.time())
        
        # Шаг 1: Создание тестового контакта
        logger.info("1️⃣ Создание тестового контакта")
        
        phone = f"+7999{timestamp % 10000000}"
        contact_data = {
            "first_name": "Быстрый",
            "last_name": f"Тест{timestamp}",
            "phone": phone,
            "comment": f"Тестовый контакт для быстрой проверки (timestamp: {timestamp})"
        }
        
        contact = await api.create_contact(**contact_data)
        
        if not contact or 'id' not in contact:
            logger.error(f"❌ Не удалось создать контакт: {contact}")
            return False
            
        contact_id = contact['id']
        logger.info(f"✅ Контакт создан: ID={contact_id}, Имя={contact.get('name')}")
        
        # Шаг 2: Создание тестовой заявки с привязкой по ID
        logger.info("2️⃣ Создание тестовой заявки с привязкой по ID")
        
        issue_data = {
            "title": f"Быстрый тест исправлений {timestamp}",
            "description": f"Тестовая заявка для быстрой проверки исправлений (timestamp: {timestamp})",
            "contact_id": contact_id,
            "telegram_id": f"test{timestamp}"
        }
        
        issue = await api.create_issue(**issue_data)
        
        if not issue or 'id' not in issue:
            logger.error(f"❌ Не удалось создать заявку: {issue}")
            return False
            
        issue_id = issue['id']
        logger.info(f"✅ Заявка создана: ID={issue_id}")
        
        # Пауза для обработки данных на стороне Okdesk
        logger.info("⏳ Ожидание обработки данных (3 секунды)...")
        await asyncio.sleep(3)
        
        # Шаг 3: Проверка привязки клиента к заявке
        logger.info("3️⃣ Проверка привязки клиента к заявке")
        
        issue_details = await api.get_issue(issue_id)
        
        if issue_details and 'contact' in issue_details and issue_details['contact']:
            contact_info = issue_details.get('contact')
            if contact_info.get('id') == contact_id:
                logger.info(f"✅ Клиент успешно привязан к заявке")
                client_binding_status = True
            else:
                logger.error(f"❌ К заявке привязан неверный клиент: {contact_info}")
                logger.error(f"   Ожидался ID: {contact_id}, Получен: {contact_info.get('id')}")
                client_binding_status = False
        else:
            logger.error(f"❌ К заявке не привязан клиент")
            client_binding_status = False
        
        # Шаг 4: Создание комментария с автором
        logger.info("4️⃣ Создание комментария с автором")
        
        comment_text = f"Тестовый комментарий для проверки привязки автора (timestamp: {timestamp})"
        comment = await api.create_comment(
            issue_id=issue_id,
            content=comment_text,
            contact_id=contact_id
        )
        
        if not comment or 'id' not in comment:
            logger.error(f"❌ Не удалось создать комментарий: {comment}")
            return False
            
        comment_id = comment['id']
        logger.info(f"✅ Комментарий создан: ID={comment_id}")
        
        # Пауза для обработки данных на стороне Okdesk
        logger.info("⏳ Ожидание обработки данных (3 секунды)...")
        await asyncio.sleep(3)
        
        # Шаг 5: Проверка автора комментария
        logger.info("5️⃣ Проверка автора комментария")
        
        # Получаем комментарии заявки
        comments = await api.get_issue_comments(issue_id)
        
        if not comments:
            logger.error("❌ Не удалось получить комментарии заявки")
            return False
            
        # Ищем наш комментарий
        comment_author_status = False
        for comment in comments:
            if comment.get('id') == comment_id:
                author = comment.get('author')
                
                if author:
                    author_id = author.get('id')
                    author_name = author.get('name')
                    
                    if author_id == contact_id:
                        logger.info(f"✅ Комментарий имеет правильного автора: {author_name}")
                        comment_author_status = True
                    else:
                        logger.error(f"❌ Комментарий имеет неверного автора: {author_name}")
                        logger.error(f"   Ожидался ID: {contact_id}, Получен: {author_id}")
                else:
                    logger.error(f"❌ Комментарий не имеет автора")
                break
        
        # Выводим итоги
        logger.info("\n🏁 ИТОГИ ПРОВЕРКИ:")
        
        if client_binding_status:
            logger.info("✅ Привязка клиентов к заявкам: РАБОТАЕТ")
        else:
            logger.info("❌ Привязка клиентов к заявкам: НЕ РАБОТАЕТ")
            
        if comment_author_status:
            logger.info("✅ Привязка авторов к комментариям: РАБОТАЕТ")
        else:
            logger.info("❌ Привязка авторов к комментариям: НЕ РАБОТАЕТ")
            
        logger.info(f"\n📋 Тестовые данные:")
        logger.info(f"   Дата и время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   Контакт: ID={contact_id}, Имя={contact.get('name')}")
        logger.info(f"   Телефон: {phone}")
        logger.info(f"   Заявка: ID={issue_id}")
        logger.info(f"   Комментарий: ID={comment_id}")
        
        return client_binding_status and comment_author_status
                
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при проверке: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await api.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Быстрая проверка исправлений бота Okdesk')
    parser.add_argument('--debug', action='store_true', help='Включить подробное логирование')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger('services.okdesk_api').setLevel(logging.DEBUG)
        
    result = asyncio.run(quick_check_fixes())
    sys.exit(0 if result else 1)
