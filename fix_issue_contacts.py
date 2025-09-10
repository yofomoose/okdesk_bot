"""
Скрипт для проверки и исправления привязки контактов и компаний в заявках
"""
import asyncio
import logging
import sys
from services.okdesk_api import OkdeskAPI
from services.database import DatabaseManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def fix_issue_contacts():
    """Исправление привязки контактов к заявкам"""
    logger.info("Начинаем исправление привязки контактов к заявкам...")
    
    db = DatabaseManager('okdesk_bot.db')
    api = OkdeskAPI()
    
    # Получаем все заявки из базы данных
    issues = db.fetch_all("SELECT issue_id, telegram_id FROM issues")
    logger.info(f"Найдено {len(issues)} заявок в базе данных")
    
    for issue_id, telegram_id in issues:
        # Получаем информацию о пользователе
        user = db.fetch_one(
            "SELECT phone, okdesk_contact_id, company_id FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        
        if not user:
            logger.warning(f"Не найден пользователь для заявки {issue_id}, telegram_id={telegram_id}")
            continue
        
        phone, okdesk_contact_id, company_id = user
        
        # Проверяем наличие привязки контакта
        if not okdesk_contact_id:
            if phone:
                logger.info(f"Поиск контакта для заявки {issue_id} по телефону {phone}")
                contact = await api.find_contact_by_phone(phone)
                
                if contact and 'id' in contact:
                    # Обновляем ID контакта в базе данных
                    okdesk_contact_id = contact['id']
                    db.update_okdesk_contact_id(telegram_id, okdesk_contact_id)
                    logger.info(f"Найден контакт: ID={okdesk_contact_id}")
            
        # Получаем информацию о заявке в OkDesk
        okdesk_issue = await api.get_issue(issue_id)
        
        if not okdesk_issue:
            logger.warning(f"Не удалось получить информацию о заявке {issue_id} из OkDesk")
            continue
        
        # Проверяем привязку клиента
        client = okdesk_issue.get('client', {})
        contact = client.get('contact', {})
        company = client.get('company', {})
        
        contact_needs_update = okdesk_contact_id and (not contact or contact.get('id') != okdesk_contact_id)
        company_needs_update = company_id and (not company or company.get('id') != company_id)
        
        if contact_needs_update or company_needs_update:
            logger.info(f"Требуется обновление привязки для заявки {issue_id}")
            
            # Создаем объект клиента для обновления
            client_update = {}
            
            if contact_needs_update:
                client_update['contact'] = {'id': okdesk_contact_id}
                logger.info(f"Обновляем привязку контакта: {okdesk_contact_id}")
            
            if company_needs_update:
                client_update['company'] = {'id': company_id}
                logger.info(f"Обновляем привязку компании: {company_id}")
            
            # Обновляем заявку
            # Примечание: метод update_issue нужно добавить в OkdeskAPI
            result = await api.update_issue(issue_id, {'client': client_update})
            
            if result:
                logger.info(f"✅ Успешно обновлена привязка для заявки {issue_id}")
            else:
                logger.error(f"❌ Не удалось обновить привязку для заявки {issue_id}")
    
    logger.info("Исправление привязки контактов завершено")

async def main():
    await fix_issue_contacts()

if __name__ == "__main__":
    asyncio.run(main())
