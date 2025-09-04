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
    
    async def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Выполнить HTTP запрос к API"""
        if not self.session:
            self.session = await self._get_session()
            
        # Поскольку в base_url уже есть /api/v1, просто добавляем endpoint
        url = f"{self.base_url}{endpoint}"
        
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
            # Используем корректный endpoint для заявок
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
    
    async def add_comment(self, issue_id: int, content: str, is_public: bool = True, author_id: int = None) -> Dict:
        """Добавить комментарий к заявке"""
        data = {
            'content': content,
            'public': is_public
        }
        
        # Добавляем author_id если указан
        if author_id:
            data['author_id'] = author_id
        
        response = await self._make_request('POST', f'/issues/{issue_id}/comments', data)
        return response if response else {}
    
    async def get_current_user(self) -> Dict:
        """Получить информацию о текущем пользователе API"""
        # Пробуем разные endpoints для получения информации о пользователе
        endpoints_to_try = ['/account', '/users/current', '/user', '/profile']
        
        for endpoint in endpoints_to_try:
            response = await self._make_request('GET', endpoint)
            if response:
                return response
        
        # Если ни один endpoint не работает, возвращаем заглушку
        logger.warning("Не удалось получить информацию о текущем пользователе через API")
        return {'id': 1}  # Используем заглушку
    
    async def get_contacts(self, limit: int = 50, **filters) -> List[Dict]:
        """Получить список контактов"""
        try:
            # Используем корректный endpoint для контактов
            endpoint = f"/contacts?limit={limit}"
            
            # Добавляем фильтры если они есть
            for key, value in filters.items():
                if value:
                    endpoint += f"&{key}={value}"
            
            response = await self._make_request('GET', endpoint)
            
            if not response:
                return []
            
            # API может возвращать как массив, так и единичный объект
            if isinstance(response, list):
                return response
            elif isinstance(response, dict):
                # Если есть поле data с массивом
                if 'data' in response:
                    return response['data']
                # Если возвращается единичный контакт (например, при поиске по телефону)
                elif 'id' in response:
                    return [response]
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

    async def get_companies(self, limit: int = 50) -> List[Dict]:
        """Получить список компаний"""
        try:
            endpoint = f"/companies?limit={limit}"
            response = await self._make_request('GET', endpoint)
            
            if not response:
                return []
            
            if isinstance(response, list):
                return response
            elif isinstance(response, dict) and 'data' in response:
                return response['data']
            return []
        except Exception as e:
            logger.error(f"Ошибка получения компаний: {e}")
            return []

    async def search_company_by_inn(self, inn: str) -> Optional[Dict]:
        """Поиск компании по ИНН"""
        try:
            logger.info(f"Ищем компанию с ИНН: {inn}")
            
            # Получаем список компаний
            companies = await self.get_companies(100)
            
            # Ищем компанию с нужным ИНН в параметрах
            for company in companies:
                # Проверяем разные поля где может храниться ИНН
                if (company.get('inn') == inn or 
                    company.get('legal_inn') == inn or
                    company.get('tax_number') == inn):
                    logger.info(f"Найдена компания с ИНН {inn}: {company.get('name')}")
                    return company
                
                # Также проверяем параметры компании
                parameters = company.get('parameters', [])
                if parameters:
                    for param in parameters:
                        if isinstance(param, dict):
                            param_name = param.get('name', '').lower()
                            param_value = str(param.get('value', ''))
                            
                            # Проверяем разные варианты названий поля ИНН
                            if any(inn_field in param_name for inn_field in ['инн', 'inn', 'ИНН']):
                                if param_value == inn:
                                    logger.info(f"Найдена компания с ИНН {inn}: {company.get('name')}")
                                    return company
            
            logger.info(f"Компания с ИНН {inn} не найдена")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка поиска компании по ИНН: {e}")
            return None

    async def test_connection(self) -> bool:
        """Тестировать соединение с API"""
        try:
            # Пробуем получить список компаний как в примере
            response = await self._make_request('GET', '/companies?limit=1')
            if response is not None:
                logger.info("✅ Соединение с Okdesk API успешно!")
                return True
            else:
                logger.error("❌ Не удалось подключиться к Okdesk API")
                return False
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования API: {e}")
            return False
