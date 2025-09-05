"""
Клиент для работы с Okdesk API - новая версия с токеном в URL
"""
import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional
import config

logger = logging.getLogger(__name__)

class OkdeskAPI:
    """Класс для работы с API Okdesk"""
    
    def __init__(self):
        self.base_url = config.OKDESK_API_URL
        self.token = config.OKDESK_API_TOKEN
        self.session = None
        
    async def __aenter__(self):
        self.session = await self._get_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def close(self):
        """Закрыть сессию"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить HTTP сессию"""
        return aiohttp.ClientSession(
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        )
    
    async def _make_request(self, method: str, endpoint: str, data: Dict = None, headers: Dict = None, params: Dict = None) -> Dict:
        """Выполнить HTTP запрос к API"""
        if not self.session:
            self.session = await self._get_session()
            
        # Формируем полный URL с токеном как в примере
        if self.base_url.endswith('/api/v1'):
            url = f"{self.base_url}{endpoint}"
        else:
            url = f"{self.base_url}/api/v1{endpoint}"
        
        # Добавляем API токен в параметры
        if '?' in endpoint:
            url += f"&api_token={self.token}"
        else:
            url += f"?api_token={self.token}"
            
        logger.info(f"{method} {url}")
        
        try:
            async with self.session.request(method, url, json=data) as response:
                response_text = await response.text()
                logger.info(f"Response status: {response.status}")
                logger.info(f"Response: {response_text[:500]}")
                
                if response.status in [200, 201]:
                    try:
                        return await response.json()
                    except:
                        return {"success": True, "text": response_text}
                else:
                    logger.error(f"API Error {response.status}: {response_text}")
                    return None
        except Exception as e:
            logger.error(f"API Error: {e}")
            return None
    
    async def get_issues(self, limit: int = 50) -> List[Dict]:
        """Получить список заявок"""
        try:
            # Конвертируем параметры в строку запроса вручную
            endpoint = f"/issues?limit={limit}"
            
            response = await self._make_request('GET', endpoint)
            
            if not response:
                return []
            
            # API возвращает данные в разных форматах
            if isinstance(response, dict):
                # Если есть поле data с массивом
                if 'data' in response:
                    return response['data']
                # Если есть поле issues с массивом  
                elif 'issues' in response:
                    return response['issues']
                # Если сам объект содержит заявки
                elif 'id' in response:
                    return [response]
            elif isinstance(response, list):
                return response
                
            return []
        except Exception as e:
            logger.error(f"Ошибка получения заявок: {e}")
            return []
    
    async def get_issue(self, issue_id: int) -> Dict:
        """Получить заявку по ID"""
        response = await self._make_request('GET', f'/issues/{issue_id}')
        return response if response else {}
    
    async def create_issue(self, title: str, description: str, **kwargs) -> Dict:
        """Создать новую заявку"""
        data = {
            'title': title,
            'description': description,
            'type_id': kwargs.get('type_id', 1),  # Тип заявки по умолчанию
            'priority_id': kwargs.get('priority_id', 2),  # Приоритет по умолчанию
            'status_id': kwargs.get('status_id', 1),  # Статус по умолчанию
        }
        
        # Добавляем дополнительные параметры если они есть
        if 'contact_id' in kwargs:
            data['contact_id'] = kwargs['contact_id']
        if 'company_id' in kwargs:
            data['company_id'] = kwargs['company_id']
        if 'assignee_id' in kwargs:
            data['assignee_id'] = kwargs['assignee_id']
        
        logger.info(f"Создаем заявку с данными: {data}")
        response = await self._make_request('POST', '/issues', data)
        return response if response else {}
    
    async def add_comment(self, issue_id: int, content: str, is_public: bool = True, 
                         author_id: int = None, author_type: str = None, 
                         author_name: str = None, client_phone: str = None, 
                         contact_auth_code: str = None, contact_id: int = None) -> Dict:
        """
        Добавить комментарий к заявке
        
        Args:
            issue_id: ID заявки
            content: Текст комментария  
            is_public: Публичный комментарий (по умолчанию True)
            author_id: ID автора комментария
            author_type: Тип автора ('contact' или 'employee')
            author_name: Имя автора (для системных комментариев)
            contact_id: ID контакта (устаревший параметр, используйте author_id + author_type)
        """
        
        # Если есть код авторизации контакта, сначала пробуем его (экспериментальная функция)
        if contact_auth_code:
            logger.info("Попытка создать комментарий с кодом авторизации контакта")
            auth_response = await self.add_comment_as_contact(issue_id, content, contact_auth_code)
            if auth_response and ('id' in auth_response or auth_response.get('success')):
                logger.info("✅ Комментарий создан с кодом авторизации")
                return auth_response
            logger.info("Код авторизации не сработал, используем системного пользователя")
        
        # Основная логика создания комментария
        data = {
            'content': content,
            'public': is_public  # Всегда публичные для клиентов
        }
        
        # Если указан контакт как автор - пытаемся создать от его имени
        if author_type == "contact" and author_id:
            data['author_id'] = author_id
            data['author_type'] = "contact"
            logger.info(f"Создаем комментарий от контакта (ID: {author_id})")
        else:
            # Иначе создаем от системного пользователя с форматированием имени
            if not config.OKDESK_SYSTEM_USER_ID:
                logger.error("❌ Системный пользователь не настроен (OKDESK_SYSTEM_USER_ID)")
                return {}
            
            data['author_id'] = config.OKDESK_SYSTEM_USER_ID
            data['author_type'] = "employee"
            logger.info(f"Устанавливаем author_type=employee для системного пользователя")
            
            # Форматируем комментарий с указанием имени клиента
            if author_name:
                data['content'] = f"💬 **{author_name}** (через Telegram бот):\n\n{content}"
            
            logger.info(f"Создаем комментарий от системного пользователя (ID: {config.OKDESK_SYSTEM_USER_ID})")
        
        # Фильтруем None значения
        if data:
            data = {k: v for k, v in data.items() if v is not None}
        
        logger.info(f"Финальные данные для отправки: {data}")
        response = await self._make_request('POST', f'/issues/{issue_id}/comments', data)
        
        if response and 'id' in response:
            logger.info(f"✅ Комментарий создан (ID: {response['id']})")
        else:
            logger.error(f"❌ Не удалось создать комментарий: {response}")
        
        return response if response else {}
    
    async def add_comment_as_contact(self, issue_id: int, content: str, contact_auth_code: str = None) -> Dict:
        """Добавить комментарий от имени контакта используя код авторизации"""
        if not contact_auth_code:
            return {}
            
        try:
            # Согласно документации, для комментариев от контактов используется endpoint без api_token
            # Извлекаем базовый URL без токена
            if '?' in self.base_url:
                base_url_clean = self.base_url.split('?')[0]
            else:
                base_url_clean = self.base_url
            
            comment_url = f"{base_url_clean}/issues/{issue_id}/comments"
            
            data = {
                'content': content,
                'public': True,
                'contact_auth_code': contact_auth_code
            }
            
            logger.info(f"Отправка комментария от контакта с кодом авторизации")
            logger.info(f"URL: {comment_url}")
            
            if not self.session:
                self.session = await self._get_session()
            
            async with self.session.post(comment_url, json=data) as resp:
                logger.info(f"Response status: {resp.status}")
                response_text = await resp.text()
                logger.info(f"Response: {response_text}")
                
                if resp.status in [200, 201]:
                    if response_text:
                        try:
                            result = await resp.json()
                            logger.info(f"✅ Комментарий создан от контакта: ID {result.get('id')}")
                            return result
                        except:
                            logger.info(f"✅ Комментарий создан от контакта (без JSON ответа)")
                            return {"success": True}
                    return {"success": True}
                else:
                    logger.error(f"API Error {resp.status}: {response_text}")
                    return {}
        except Exception as e:
            logger.error(f"Ошибка при отправке комментария от контакта: {e}")
            return {}
    
    async def get_contacts(self, limit: int = 50) -> List[Dict]:
        """Получить список контактов"""
        try:
            endpoint = f"/contacts?limit={limit}"
            response = await self._make_request('GET', endpoint)
            
            if not response:
                return []
            
            if isinstance(response, list):
                return response
            elif isinstance(response, dict) and 'data' in response:
                return response['data']
            return []
        except Exception as e:
            logger.error(f"Ошибка получения контактов: {e}")
            return []
    
    async def search_contact_by_phone(self, phone: str) -> Optional[Dict]:
        """Найти контакт по номеру телефона"""
        try:
            contacts = await self.get_contacts(100)  # Получаем больше контактов для поиска
            for contact in contacts:
                # Сравниваем телефоны (убираем все лишние символы)
                contact_phone = contact.get('phone', '').replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
                search_phone = phone.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
                if contact_phone == search_phone:
                    logger.info(f"Найден контакт: {contact.get('name', 'Без имени')} (ID: {contact.get('id')})")
                    return contact
            return None
        except Exception as e:
            logger.error(f"Ошибка поиска контакта: {e}")
            return None
    
    async def create_contact(self, first_name: str, last_name: str, **kwargs) -> Dict:
        """Создать новый контакт"""
        data = {
            'first_name': first_name,
            'last_name': last_name
        }
        
        # Добавляем дополнительные поля
        for field in ['phone', 'email', 'company_id', 'position', 'comment']:
            if field in kwargs and kwargs[field]:
                data[field] = kwargs[field]
        
        logger.info(f"Создаем контакт с данными: {data}")
        response = await self._make_request('POST', '/contacts', data)
        return response if response else {}

    async def test_connection(self) -> bool:
        """Тестировать соединение с API"""
        try:
            # Пробуем получить список заявок (простой запрос)
            response = await self._make_request('GET', '/issues?limit=1')
            if response is not None:
                logger.info("✅ Соединение с Okdesk API успешно!")
                return True
            else:
                logger.error("❌ Не удалось подключиться к Okdesk API")
                return False
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования API: {e}")
            return False
