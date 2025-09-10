"""
Скрипт для массовой синхронизации ID контактов и компаний с OkDesk
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

async def sync_all_users():
    """Синхронизировать всех пользователей с API Okdesk"""
    db = DatabaseManager('okdesk_bot.db')
    api = OkdeskAPI()
    
    # Получаем всех пользователей из базы данных
    users = db.fetch_all("SELECT telegram_id, phone, inn FROM users")
    logger.info(f"Найдено {len(users)} пользователей в базе данных")
    
    contacts_synced = 0
    companies_synced = 0
    
    for user in users:
        telegram_id, phone, inn = user
        logger.info(f"Обрабатываем пользователя {telegram_id}, телефон: {phone}, ИНН: {inn}")
        
        # Синхронизация контакта
        if phone:
            contact = await api.find_contact_by_phone(phone)
            if contact and 'id' in contact:
                contacts_synced += 1
                logger.info(f"Найден контакт: ID={contact['id']}, Имя={contact.get('name', 'Без имени')}")
                db.update_okdesk_contact_id(telegram_id, contact['id'])
        
        # Синхронизация компании
        if inn:
            company = await api.find_company_by_inn(inn)
            if company and 'id' in company:
                companies_synced += 1
                logger.info(f"Найдена компания: ID={company['id']}, Название={company.get('name', 'Без названия')}")
                db.update_okdesk_company_id(telegram_id, company['id'])
    
    logger.info(f"Синхронизация завершена. Обновлено контактов: {contacts_synced}, компаний: {companies_synced}")

async def main():
    await sync_all_users()

if __name__ == "__main__":
    asyncio.run(main())
