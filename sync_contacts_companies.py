"""
Скрипт для проверки и массовой привязки контактов и компаний для пользователей в базе данных
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

async def main():
    logger.info("Начинаем проверку и привязку контактов и компаний...")
    
    api = OkdeskAPI()
    db = DatabaseManager('okdesk_bot.db')
    
    # 1. Обработка пользователей без привязанного контакта
    users_without_contact = db.execute(
        "SELECT telegram_id, phone, full_name FROM users WHERE okdesk_contact_id IS NULL AND phone IS NOT NULL"
    ).fetchall()
    
    logger.info(f"Найдено {len(users_without_contact)} пользователей без привязанного контакта")
    
    for user_id, phone, full_name in users_without_contact:
        if not phone:
            continue
            
        logger.info(f"Обрабатываем пользователя: {user_id}, {full_name}, {phone}")
        
        # Поиск контакта по телефону
        contact = await api.find_contact_by_phone(phone)
        
        if not contact:
            # Если контакт не найден, создаем новый
            logger.info(f"Создаем новый контакт для пользователя {user_id}")
            
            # Разделяем имя на имя и фамилию
            first_name = full_name.split()[0] if full_name and ' ' in full_name else "Пользователь"
            last_name = ' '.join(full_name.split()[1:]) if full_name and len(full_name.split()) > 1 else "Telegram"
            
            contact = await api.create_contact(
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                comment=f"Контакт создан автоматически из Telegram для пользователя {user_id}"
            )
            
        if contact and 'id' in contact:
            # Обновляем ID контакта в базе данных
            db.execute(
                "UPDATE users SET okdesk_contact_id = ? WHERE telegram_id = ?",
                (contact['id'], user_id)
            )
            db.commit()
            logger.info(f"✅ Контакт ID={contact['id']} привязан к пользователю {user_id}")
    
    # 2. Обработка пользователей без привязанной компании, но с ИНН
    users_without_company = db.execute(
        "SELECT telegram_id, inn FROM users WHERE okdesk_company_id IS NULL AND inn IS NOT NULL AND inn != ''"
    ).fetchall()
    
    logger.info(f"Найдено {len(users_without_company)} пользователей без привязанной компании, но с ИНН")
    
    for user_id, inn in users_without_company:
        if not inn:
            continue
            
        logger.info(f"Обрабатываем пользователя: {user_id}, ИНН: {inn}")
        
        # Поиск компании по ИНН
        company = await api.find_company_by_inn(inn)
        
        if company and 'id' in company:
            # Обновляем ID компании в базе данных
            db.execute(
                "UPDATE users SET okdesk_company_id = ? WHERE telegram_id = ?",
                (company['id'], user_id)
            )
            db.commit()
            logger.info(f"✅ Компания ID={company['id']} привязана к пользователю {user_id}")
    
    # 3. Вывод статистики после обработки
    total_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    users_with_contact = db.execute("SELECT COUNT(*) FROM users WHERE okdesk_contact_id IS NOT NULL").fetchone()[0]
    users_with_company = db.execute("SELECT COUNT(*) FROM users WHERE okdesk_company_id IS NOT NULL").fetchone()[0]
    
    logger.info(f"Статистика после обработки:")
    logger.info(f"Всего пользователей: {total_users}")
    logger.info(f"Пользователей с привязанным контактом: {users_with_contact} ({users_with_contact/total_users*100:.1f}%)")
    logger.info(f"Пользователей с привязанной компанией: {users_with_company} ({users_with_company/total_users*100:.1f}%)")
    
    logger.info("Проверка и привязка контактов и компаний завершена")
    db.close()

if __name__ == "__main__":
    asyncio.run(main())
