#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
import os
import logging
import time
import json

# Добавляем путь к корневой директории проекта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.okdesk_api import OkdeskAPI
from services.database import DatabaseManager

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                   format='%(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

# Включаем вывод запросов API
logging.getLogger('services.okdesk_api').setLevel(logging.DEBUG)

async def full_workflow_diagnosis():
    """Полная диагностика процесса создания контактов и заявок с привязкой"""
    
    logger.info("🚀 Запуск полной диагностики")
    
    # Создаем экземпляр API клиента
    api = OkdeskAPI()
    db = DatabaseManager('okdesk_bot.db')
    
    try:
        timestamp = int(time.time())
        
        logger.info("📊 Информация о системе:")
        logger.info(f"   Timestamp: {timestamp}")
        
        # Шаг 1: Проверка доступности API
        logger.info("1️⃣ Проверка доступности API Okdesk")
        
        companies = await api.get_companies_list(per_page=1)
        if companies:
            logger.info(f"✅ API Okdesk доступен")
        else:
            logger.error(f"❌ Не удалось получить доступ к API Okdesk")
            return False
            
        # Шаг 2: Создание контакта
        logger.info("2️⃣ Создание тестового контакта")
        
        phone = f"+7999{timestamp % 10000000}"
        telegram_id = f"test{timestamp}"
        
        contact_data = {
            "first_name": "Тест",
            "last_name": f"Диагностика{timestamp}",
            "phone": phone,
            "comment": f"Тестовый контакт для полной диагностики (timestamp: {timestamp}, telegram_id: {telegram_id})"
        }
        
        # Сохраняем данные пользователя в базу данных бота
        logger.info("   Сохранение пользователя в базу данных бота")
        user_data = {
            "telegram_id": telegram_id,
            "first_name": contact_data["first_name"],
            "last_name": contact_data["last_name"],
            "phone": phone,
            "created_at": timestamp,
            "okdesk_contact_id": None  # Будет обновлено позже
        }
        
        db.execute(
            """
            INSERT OR REPLACE INTO users 
            (telegram_id, first_name, last_name, phone, created_at, okdesk_contact_id) 
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_data["telegram_id"], 
                user_data["first_name"], 
                user_data["last_name"], 
                user_data["phone"], 
                user_data["created_at"], 
                user_data["okdesk_contact_id"]
            )
        )
        db.commit()
        logger.info(f"✅ Пользователь сохранен в базу данных бота")
        
        # Создаем контакт в Okdesk
        contact = await api.create_contact(**contact_data)
        
        if not contact or 'id' not in contact:
            logger.error(f"❌ Не удалось создать контакт: {contact}")
            return False
            
        contact_id = contact['id']
        logger.info(f"✅ Контакт создан в Okdesk: ID={contact_id}, Имя={contact.get('name')}")
        
        # Обновляем ID контакта в базе данных бота
        db.execute(
            "UPDATE users SET okdesk_contact_id = ? WHERE telegram_id = ?",
            (contact_id, telegram_id)
        )
        db.commit()
        logger.info(f"✅ ID контакта обновлен в базе данных бота")
        
        # Шаг 3: Проверка поиска контакта по телефону
        logger.info("3️⃣ Проверка поиска контакта по телефону")
        
        # Проверяем разные форматы телефона
        phone_formats = [
            phone,
            phone.replace("+", ""),
            phone.replace("+7", "8"),
            phone[-10:],  # Последние 10 цифр
        ]
        
        for format_phone in phone_formats:
            logger.info(f"   Поиск контакта по телефону: {format_phone}")
            found_contact = await api.find_contact_by_phone(format_phone)
            
            if found_contact and found_contact.get('id') == contact_id:
                logger.info(f"✅ Контакт успешно найден по формату телефона: {format_phone}")
            else:
                if found_contact:
                    logger.warning(f"⚠️ По формату {format_phone} найден другой контакт: {found_contact}")
                else:
                    logger.warning(f"⚠️ Контакт не найден по формату телефона: {format_phone}")
        
        # Шаг 4: Создание заявки с привязкой по contact_id
        logger.info("4️⃣ Создание заявки с привязкой по contact_id")
        
        issue_data = {
            "title": f"Тест диагностики (contact_id) {timestamp}",
            "description": f"Тестовая заявка для проверки привязки по contact_id (timestamp: {timestamp})",
            "contact_id": contact_id,
            "telegram_id": telegram_id
        }
        
        issue1 = await api.create_issue(**issue_data)
        
        if not issue1 or 'id' not in issue1:
            logger.error(f"❌ Не удалось создать заявку: {issue1}")
            return False
            
        issue1_id = issue1['id']
        logger.info(f"✅ Заявка создана: ID={issue1_id}")
        
        # Шаг 5: Проверка привязки в первой заявке
        logger.info("5️⃣ Проверка привязки клиента к первой заявке")
        
        issue1_details = await api.get_issue(issue1_id)
        
        if issue1_details and 'contact' in issue1_details:
            contact_info = issue1_details.get('contact')
            if contact_info and contact_info.get('id') == contact_id:
                logger.info(f"✅ Клиент успешно привязан к первой заявке: {contact_info}")
                
                # Выводим детали клиента в заявке
                logger.info(f"   ID: {contact_info.get('id')}")
                logger.info(f"   Имя: {contact_info.get('name')}")
            else:
                logger.error(f"❌ Клиент не привязан или привязан неверный: {contact_info}")
                logger.error(f"   Ожидался ID: {contact_id}, Получен: {contact_info.get('id') if contact_info else 'None'}")
        else:
            logger.error(f"❌ В первой заявке нет информации о клиенте")
            
        # Сохраняем связь заявки с телеграм пользователем в базе данных бота
        db.execute(
            """
            INSERT INTO issues 
            (issue_id, telegram_id, created_at) 
            VALUES (?, ?, ?)
            """,
            (issue1_id, telegram_id, timestamp)
        )
        db.commit()
        logger.info(f"✅ Связь заявки с пользователем сохранена в базу данных бота")
        
        # Шаг 6: Создание заявки с привязкой по телефону
        logger.info("6️⃣ Создание заявки с привязкой по телефону")
        
        issue_data = {
            "title": f"Тест диагностики (phone) {timestamp}",
            "description": f"Тестовая заявка для проверки привязки по телефону (timestamp: {timestamp})",
            "phone": phone,
            "telegram_id": telegram_id,
            "full_name": f"{contact_data['first_name']} {contact_data['last_name']}"
        }
        
        issue2 = await api.create_issue(**issue_data)
        
        if not issue2 or 'id' not in issue2:
            logger.error(f"❌ Не удалось создать вторую заявку: {issue2}")
            return False
            
        issue2_id = issue2['id']
        logger.info(f"✅ Вторая заявка создана: ID={issue2_id}")
        
        # Шаг 7: Проверка привязки во второй заявке
        logger.info("7️⃣ Проверка привязки клиента ко второй заявке")
        
        issue2_details = await api.get_issue(issue2_id)
        
        if issue2_details and 'contact' in issue2_details:
            contact_info = issue2_details.get('contact')
            if contact_info and contact_info.get('id') == contact_id:
                logger.info(f"✅ Клиент успешно привязан ко второй заявке: {contact_info}")
                
                # Выводим детали клиента в заявке
                logger.info(f"   ID: {contact_info.get('id')}")
                logger.info(f"   Имя: {contact_info.get('name')}")
            else:
                logger.error(f"❌ Клиент не привязан или привязан неверный: {contact_info}")
                logger.error(f"   Ожидался ID: {contact_id}, Получен: {contact_info.get('id') if contact_info else 'None'}")
        else:
            logger.error(f"❌ Во второй заявке нет информации о клиенте")
            
        # Сохраняем связь заявки с телеграм пользователем в базе данных бота
        db.execute(
            """
            INSERT INTO issues 
            (issue_id, telegram_id, created_at) 
            VALUES (?, ?, ?)
            """,
            (issue2_id, telegram_id, timestamp)
        )
        db.commit()
        logger.info(f"✅ Связь второй заявки с пользователем сохранена в базу данных бота")
        
        # Шаг 8: Создание комментария к заявке с указанием автора
        logger.info("8️⃣ Создание комментария с явным указанием автора")
        
        comment_text = f"Тестовый комментарий для диагностики с автором (timestamp: {timestamp})"
        comment = await api.create_comment(
            issue_id=issue1_id,
            content=comment_text,
            contact_id=contact_id
        )
        
        if not comment or 'id' not in comment:
            logger.error(f"❌ Не удалось создать комментарий: {comment}")
            return False
            
        comment_id = comment['id']
        logger.info(f"✅ Комментарий создан: ID={comment_id}")
        
        # Шаг 9: Проверка комментария
        logger.info("9️⃣ Проверка созданного комментария")
        
        # Получаем комментарии заявки
        comments = await api.get_issue_comments(issue1_id)
        
        if not comments:
            logger.error("❌ Не удалось получить комментарии заявки")
            return False
            
        # Ищем наш комментарий
        found = False
        for comment in comments:
            if comment.get('id') == comment_id:
                found = True
                author = comment.get('author')
                
                if author:
                    author_id = author.get('id')
                    author_name = author.get('name')
                    
                    if author_id == contact_id:
                        logger.info(f"✅ Комментарий имеет правильного автора: ID={author_id}, Имя={author_name}")
                    else:
                        logger.error(f"❌ Комментарий имеет неверного автора: ID={author_id}, Имя={author_name}")
                        logger.error(f"   Ожидался ID: {contact_id}")
                else:
                    logger.error(f"❌ Комментарий не имеет автора")
                    
                logger.info(f"✅ Содержимое комментария: {comment.get('content')}")
                break
                
        if not found:
            logger.error(f"❌ Созданный комментарий не найден в списке комментариев заявки")
        
        # Шаг 10: Проверка связи в базе данных бота
        logger.info("🔟 Проверка связей в базе данных бота")
        
        # Проверяем запись пользователя
        user_record = db.fetch_one(
            "SELECT * FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        
        if user_record:
            logger.info(f"✅ Пользователь найден в базе данных бота:")
            logger.info(f"   Telegram ID: {user_record[0]}")
            logger.info(f"   Имя: {user_record[1]} {user_record[2]}")
            logger.info(f"   Телефон: {user_record[3]}")
            logger.info(f"   Okdesk Contact ID: {user_record[5]}")
            
            if user_record[5] == contact_id:
                logger.info(f"✅ ID контакта в базе данных бота совпадает с Okdesk")
            else:
                logger.error(f"❌ ID контакта в базе данных бота НЕ совпадает с Okdesk!")
                logger.error(f"   В БД: {user_record[5]}, в Okdesk: {contact_id}")
        else:
            logger.error(f"❌ Пользователь не найден в базе данных бота")
        
        # Проверяем связь с заявками
        issues_records = db.fetch_all(
            "SELECT * FROM issues WHERE telegram_id = ?",
            (telegram_id,)
        )
        
        if issues_records:
            logger.info(f"✅ Найдено {len(issues_records)} заявок для пользователя в БД бота:")
            
            found_issue1 = False
            found_issue2 = False
            
            for record in issues_records:
                issue_id_db = record[0]
                logger.info(f"   Заявка ID: {issue_id_db}")
                
                if issue_id_db == issue1_id:
                    found_issue1 = True
                elif issue_id_db == issue2_id:
                    found_issue2 = True
            
            if found_issue1:
                logger.info(f"✅ Первая заявка найдена в базе данных бота")
            else:
                logger.error(f"❌ Первая заявка НЕ найдена в базе данных бота")
                
            if found_issue2:
                logger.info(f"✅ Вторая заявка найдена в базе данных бота")
            else:
                logger.error(f"❌ Вторая заявка НЕ найдена в базе данных бота")
        else:
            logger.error(f"❌ Заявки не найдены в базе данных бота")
        
        # Выводим итоги
        logger.info(f"🏁 Диагностика завершена!")
        logger.info(f"📋 Итоги:")
        logger.info(f"   Контакт: ID={contact_id}, Имя={contact.get('name')}")
        logger.info(f"   Телефон: {phone}")
        logger.info(f"   Telegram ID: {telegram_id}")
        logger.info(f"   Заявка 1: ID={issue1_id}")
        logger.info(f"   Заявка 2: ID={issue2_id}")
        logger.info(f"   Комментарий: ID={comment_id}")
        
        return True
                
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при диагностике: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await api.close()
        db.close()

if __name__ == "__main__":
    result = asyncio.run(full_workflow_diagnosis())
    sys.exit(0 if result else 1)
