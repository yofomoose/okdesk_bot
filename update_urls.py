import os
import sys
from pathlib import Path
import asyncio
import logging

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from models.database import SessionLocal, Issue, User
from database.crud import IssueService, UserService
from services.okdesk_api import OkdeskAPI
import config
import config

async def update_existing_urls():
    """Обновляет URL существующих заявок на портал"""
    session = SessionLocal()

    try:
        # Получаем все заявки с URL (только необходимые поля)
        issues = session.query(Issue.id, Issue.issue_number, Issue.okdesk_url, Issue.telegram_user_id).filter(Issue.okdesk_url.isnot(None)).all()

        updated_count = 0
        api = OkdeskAPI()

        for issue_data in issues:
            issue_id_db, issue_number, okdesk_url, telegram_user_id = issue_data
            
            # Получаем данные пользователя
            user = UserService.get_user_by_telegram_id(telegram_user_id)
            user_portal_token = user.portal_token if user else None
            
            # Если у пользователя нет токена портала, но есть contact_id, попробуем получить его
            if not user_portal_token and user and user.okdesk_contact_id:
                try:
                    logger.info(f"🔄 Получаем токен портала для пользователя {telegram_user_id} (contact_id: {user.okdesk_contact_id})")
                    portal_token = await api.get_contact_portal_token(user.okdesk_contact_id)
                    if portal_token:
                        # Сохраняем токен в базе данных
                        UserService.update_portal_token_by_telegram_id(telegram_user_id, portal_token)
                        user_portal_token = portal_token
                        print(f"✅ Получен и сохранен токен портала для пользователя {telegram_user_id}")
                    else:
                        print(f"⚠️ Не удалось получить токен портала для пользователя {telegram_user_id}")
                except Exception as e:
                    print(f"❌ Ошибка при получении токена портала для пользователя {telegram_user_id}: {e}")
            
            # Проверяем, содержит ли URL API путь
            if '/api/v1' in okdesk_url or 'okdesk.ru/issues/' in okdesk_url:
                # Извлекаем ID заявки из URL
                if '/issues/' in okdesk_url:
                    parts = okdesk_url.split('/issues/')
                    if len(parts) > 1:
                        issue_id = parts[1].split('/')[0].split('?')[0]
                        
                        # Формируем новую ссылку с персональным токеном пользователя
                        if user_portal_token:
                            new_url = f"{config.OKDESK_PORTAL_URL}/login?token={user_portal_token}&redirect=/issues/{issue_id}"
                        else:
                            new_url = f"{config.OKDESK_PORTAL_URL}/issues/{issue_id}"
                        
                        print(f"Обновляю заявку #{issue_number}: {okdesk_url} -> {new_url}")

                        # Обновляем URL в базе данных
                        session.query(Issue).filter(Issue.id == issue_id_db).update({"okdesk_url": new_url})
                        updated_count += 1
                        
        session.commit()
        print(f"✅ Обновлено {updated_count} URL заявок")

    except Exception as e:
        session.rollback()
        print(f"❌ Ошибка при обновлении URL: {e}")
    finally:
        session.close()

class PortalURLGenerator:
    """Класс для генерации URL-адресов клиентского портала"""
    
    def __init__(self):
        self.api = OkdeskAPI()
        self.portal_url = config.OKDESK_PORTAL_URL
        
    async def create_login_link(self, contact_id: int, redirect_url: str = None, expire_minutes: int = 60*24*30) -> str:
        """
        Создает одноразовую ссылку для входа в портал для контакта
        
        Args:
            contact_id: ID контакта в OkDesk
            redirect_url: URL для перенаправления после входа (например, /issues/123)
            expire_minutes: Время жизни ссылки в минутах (по умолчанию 30 дней)
            
        Returns:
            str: URL для автоматического входа в портал
        """
        try:
            data = {
                'user_type': 'contact',
                'user_id': contact_id,
                'expire_after': expire_minutes,
                'one_time': False  # Многоразовая ссылка для удобства
            }
            
            logger.info(f"Создаем ссылку для входа контакта {contact_id}")
            response = await self.api._make_request('POST', 'login_link', data)
            
            if response and ('url' in response or 'login_link' in response):
                # API может возвращать либо 'url', либо 'login_link'
                login_url = response.get('url') or response.get('login_link')
                logger.info(f"✅ Создана ссылка входа: {login_url}")
                
                # Если указан redirect_url, добавляем его к ссылке
                if redirect_url:
                    # Убираем ведущий слеш из redirect_url если он есть
                    redirect_clean = redirect_url.lstrip('/')
                    # Добавляем параметр redirect к URL
                    if '?' in login_url:
                        final_url = f"{login_url}&redirect={redirect_clean}"
                    else:
                        final_url = f"{login_url}?redirect={redirect_clean}"
                    logger.info(f"✅ Добавлен redirect: {final_url}")
                    return final_url
                else:
                    return login_url
            else:
                logger.error(f"❌ Не удалось создать ссылку входа: {response}")
                # Возвращаем обычную ссылку на портал как fallback
                return self.portal_url
                
        except Exception as e:
            logger.error(f"Ошибка создания ссылки входа: {e}")
            # Возвращаем обычную ссылку на портал как fallback
            return self.portal_url
    
    async def get_issue_portal_url(self, contact_id: int, issue_id: int) -> str:
        """
        Создает URL для просмотра заявки на портале с автоматическим входом
        
        Args:
            contact_id: ID контакта в OkDesk
            issue_id: ID заявки в OkDesk
            
        Returns:
            str: URL для просмотра заявки с автоматическим входом
        """
        redirect_path = f"issues/{issue_id}"
        return await self.create_login_link(contact_id, redirect_path)
    
    async def get_portal_main_url(self, contact_id: int) -> str:
        """
        Создает URL для главной страницы портала с автоматическим входом
        
        Args:
            contact_id: ID контакта в OkDesk
            
        Returns:
            str: URL для главной страницы портала с автоматическим входом
        """
        return await self.create_login_link(contact_id)
    
    def get_simple_issue_url(self, issue_id: int) -> str:
        """
        Создает простую ссылку на заявку без автоматического входа
        
        Args:
            issue_id: ID заявки в OkDesk
            
        Returns:
            str: Простая ссылка на заявку
        """
        return f"{self.portal_url}/issues/{issue_id}"
    
    async def close(self):
        """Закрыть соединения"""
        if self.api:
            await self.api.close()


async def update_user_portal_access(telegram_id: int, contact_id: int = None) -> dict:
    """
    Обновляет доступ пользователя к порталу, создает ссылки для входа
    
    Args:
        telegram_id: Telegram ID пользователя
        contact_id: ID контакта в OkDesk (если не указан, берется из базы)
        
    Returns:
        dict: Результат обновления с ссылками
    """
    try:
        # Получаем пользователя из базы
        user = UserService.get_user_by_telegram_id(telegram_id)
        if not user:
            return {'error': 'Пользователь не найден'}
        
        # Получаем contact_id
        if not contact_id:
            contact_id = user.okdesk_contact_id
            
        if not contact_id:
            return {'error': 'Contact ID не найден для пользователя'}
        
        # Создаем генератор ссылок
        url_gen = PortalURLGenerator()
        
        try:
            # Генерируем основную ссылку на портал
            main_portal_url = await url_gen.get_portal_main_url(contact_id)
            
            result = {
                'success': True,
                'contact_id': contact_id,
                'main_portal_url': main_portal_url,
                'portal_base_url': config.OKDESK_PORTAL_URL
            }
            
            logger.info(f"✅ Обновлен доступ к порталу для пользователя {telegram_id}")
            return result
            
        finally:
            await url_gen.close()
            
    except Exception as e:
        logger.error(f"Ошибка обновления доступа к порталу: {e}")
        return {'error': str(e)}


async def get_enhanced_issue_urls(telegram_id: int, issue_id: int) -> dict:
    """
    Создает расширенные ссылки на заявку для пользователя
    
    Args:
        telegram_id: Telegram ID пользователя
        issue_id: ID заявки в OkDesk
        
    Returns:
        dict: Словарь с различными ссылками на заявку
    """
    try:
        # Получаем пользователя из базы
        user = UserService.get_user_by_telegram_id(telegram_id)
        if not user:
            return {'error': 'Пользователь не найден'}
        
        contact_id = user.okdesk_contact_id
        if not contact_id:
            return {'error': 'Contact ID не найден для пользователя'}
        
        # Создаем генератор ссылок
        url_gen = PortalURLGenerator()
        
        try:
            # Генерируем различные ссылки
            auto_login_url = await url_gen.get_issue_portal_url(contact_id, issue_id)
            simple_url = url_gen.get_simple_issue_url(issue_id)
            main_portal_url = await url_gen.get_portal_main_url(contact_id)
            
            result = {
                'success': True,
                'issue_id': issue_id,
                'contact_id': contact_id,
                'auto_login_url': auto_login_url,  # URL с автоматическим входом на заявку
                'simple_url': simple_url,          # Простая ссылка на заявку
                'main_portal_url': main_portal_url, # Главная страница портала
                'portal_base_url': config.OKDESK_PORTAL_URL
            }
            
            logger.info(f"✅ Созданы ссылки на заявку {issue_id} для пользователя {telegram_id}")
            return result
            
        finally:
            await url_gen.close()
            
    except Exception as e:
        logger.error(f"Ошибка создания ссылок на заявку: {e}")
        return {'error': str(e)}


async def test_portal_integration():
    """Функция для тестирования интеграции с порталом"""
    logger.info("🧪 Начинаем тестирование интеграции с порталом...")
    
    # Создаем тестовый контакт
    api = OkdeskAPI()
    try:
        # Создаем тестовый контакт
        test_contact = await api.create_contact(
            first_name="Тест",
            last_name="Порталов",
            phone="+79999999999",
            comment="Тестовый контакт для проверки портала"
        )
        
        if test_contact and 'id' in test_contact:
            contact_id = test_contact['id']
            logger.info(f"✅ Создан тестовый контакт ID={contact_id}")
            
            # Создаем генератор ссылок
            url_gen = PortalURLGenerator()
            try:
                # Тестируем создание ссылки входа
                login_url = await url_gen.get_portal_main_url(contact_id)
                logger.info(f"✅ Создана ссылка входа: {login_url}")
                
                # Тестируем ссылку на несуществующую заявку
                issue_url = await url_gen.get_issue_portal_url(contact_id, 1)
                logger.info(f"✅ Создана ссылка на заявку: {issue_url}")
                
                return {
                    'success': True,
                    'test_contact_id': contact_id,
                    'login_url': login_url,
                    'issue_url': issue_url
                }
                
            finally:
                await url_gen.close()
        else:
            logger.error("❌ Не удалось создать тестовый контакт")
            return {'error': 'Не удалось создать тестовый контакт'}
            
    finally:
        await api.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        # Тестирование портала
        result = asyncio.run(test_portal_integration())
        print("🧪 Результат тестирования:", result)
    else:
        # Обновление существующих URL
        asyncio.run(update_existing_urls())