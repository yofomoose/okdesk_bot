"""
Скрипт для сброса идентификаторов OkDesk контактов и компаний в базе данных
"""
import logging
import sys
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

def main():
    logger.info("Начинаем сброс идентификаторов OkDesk в базе данных...")
    
    db = DatabaseManager('okdesk_bot.db')
    
    # Проверка наличия колонок okdesk_contact_id и okdesk_company_id
    columns = [col[1] for col in db.execute("PRAGMA table_info(users)").fetchall()]
    
    if 'okdesk_contact_id' not in columns:
        logger.info("Добавляем колонку okdesk_contact_id в таблицу users")
        db.execute("ALTER TABLE users ADD COLUMN okdesk_contact_id INTEGER")
    
    if 'okdesk_company_id' not in columns:
        logger.info("Добавляем колонку okdesk_company_id в таблицу users")
        db.execute("ALTER TABLE users ADD COLUMN okdesk_company_id INTEGER")
    
    # Сбрасываем значения идентификаторов OkDesk
    db.execute("UPDATE users SET okdesk_contact_id = NULL, okdesk_company_id = NULL")
    db.commit()
    
    # Проверка результата
    users_count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    contact_id_count = db.execute("SELECT COUNT(*) FROM users WHERE okdesk_contact_id IS NOT NULL").fetchone()[0]
    company_id_count = db.execute("SELECT COUNT(*) FROM users WHERE okdesk_company_id IS NOT NULL").fetchone()[0]
    
    logger.info(f"Всего пользователей: {users_count}")
    logger.info(f"Пользователей с okdesk_contact_id: {contact_id_count}")
    logger.info(f"Пользователей с okdesk_company_id: {company_id_count}")
    
    logger.info("Сброс идентификаторов OkDesk завершен")
    db.close()

if __name__ == "__main__":
    main()
