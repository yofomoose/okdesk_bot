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
            
        # Если endpoint начинается с /api/v1, используем base_url без /api/v1
        if endpoint.startswith('/api/v1'):
            # base_url уже содержит /api/v1, поэтому берем только домен
            base = self.base_url.replace('/api/v1', '')
            url = f"{base}{endpoint}"
        else:
            # Для старых endpoints используем base_url как есть
            url = f"{self.base_url}{endpoint}"
        
        # Собираем параметры запроса
        query_params = {'api_token': self.token}
        if params:
            query_params.update(params)
        
        # Формируем URL с параметрами
        param_string = '&'.join([f"{k}={v}" for k, v in query_params.items()])
        if '?' in url:
            url += f"&{param_string}"
        else:
            url += f"?{param_string}"
            
        logger.info(f"{method} {url}")
        if headers:
            logger.info(f"Headers: {headers}")
        
        try:
            async with self.session.request(method, url, json=data, headers=headers) as response:
                response_text = await response.text()
                logger.info(f"Response status: {response.status}")
                logger.info(f"Response: {response_text[:500]}")
                logger.info(f"Request data sent: {data}")  # Отладка отправляемых данных
                
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
            # Используем правильный endpoint согласно тестированию
            response = await self._make_request(
                'GET', 
                '/api/v1/issues/list',
                params={'limit': limit}
            )
            
            if not response:
                return []
            
            # Если это уже список - возвращаем как есть
            if isinstance(response, list):
                return response
                
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
            logger.info(f"Data (без кода): {dict((k, v if k != 'contact_auth_code' else f'{v[:4]}****') for k, v in data.items())}")
            
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
            data['author_id'] = config.OKDESK_SYSTEM_USER_ID
            data['author_type'] = "employee"
            
            # Форматируем комментарий с указанием имени клиента
            if author_name:
                data['content'] = f"💬 **{author_name}** (через Telegram бот):\n\n{content}"
            
            logger.info(f"Создаем комментарий от системного пользователя (ID: {config.OKDESK_SYSTEM_USER_ID})")
        
        response = await self._make_request('POST', f'/api/v1/issues/{issue_id}/comments', data)
        
        if response and 'id' in response:
            logger.info(f"✅ Комментарий создан (ID: {response['id']})")
        else:
            logger.error(f"❌ Не удалось создать комментарий: {response}")
        
        return response if response else {}
    
    async def get_issue_comments(self, issue_id: int) -> List[Dict]:
        """Получить список комментариев заявки"""
        try:
            response = await self._make_request('GET', f'/api/v1/issues/{issue_id}/comments')
            
            if response is None:
                return []
            
            # Если ответ - список, возвращаем как есть
            if isinstance(response, list):
                return response
                
            # Если ответ - словарь, ищем комментарии в разных полях
            if isinstance(response, dict):
                # Попробуем разные варианты структуры ответа
                if 'comments' in response:
                    return response['comments']
                elif 'data' in response:
                    return response['data']
                elif 'results' in response:
                    return response['results']
                else:
                    # Если есть одиночный комментарий
                    if 'id' in response:
                        return [response]
            
            return []
            
        except Exception as e:
            logger.error(f"Ошибка при получении комментариев заявки {issue_id}: {e}")
            return []
    
    async def get_employees(self, limit: int = 50) -> List[Dict]:
        """Получить список сотрудников"""
        try:
            # Пробуем разные endpoints для получения сотрудников
            endpoints = [
                f"/users?limit={limit}",
                f"/staff?limit={limit}",
                f"/employees?limit={limit}"
            ]
            
            for endpoint in endpoints:
                try:
                    response = await self._make_request('GET', endpoint)
                    
                    if response:
                        if isinstance(response, list):
                            return response
                        elif isinstance(response, dict) and 'data' in response:
                            return response['data']
                        elif isinstance(response, dict) and 'users' in response:
                            return response['users']
                except Exception as e:
                    logger.warning(f"Endpoint {endpoint} недоступен: {e}")
                    continue
            
            logger.warning("Не удалось получить список сотрудников ни через один endpoint")
            return []
        except Exception as e:
            logger.error(f"Ошибка получения сотрудников: {e}")
            return []
    
    async def find_employee_by_name(self, full_name: str) -> Optional[Dict]:
        """Найти сотрудника по имени"""
        try:
            employees = await self.get_employees(100)
            
            # Нормализуем имя для поиска
            search_name = full_name.lower().strip()
            
            for employee in employees:
                # Проверяем разные варианты имени
                employee_name = employee.get('name', '').lower().strip()
                first_name = employee.get('first_name', '').lower().strip()
                last_name = employee.get('last_name', '').lower().strip()
                full_employee_name = f"{first_name} {last_name}".strip()
                
                if (employee_name == search_name or 
                    full_employee_name == search_name or
                    search_name in employee_name or
                    search_name in full_employee_name):
                    logger.info(f"Найден сотрудник: {employee.get('name', full_employee_name)} (ID: {employee.get('id')})")
                    return employee
            
            logger.info(f"Сотрудник с именем '{full_name}' не найден")
            return None
        except Exception as e:
            logger.error(f"Ошибка поиска сотрудника: {e}")
            return None
    
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
        for field in ['phone', 'email', 'company_id', 'position', 'comment', 'login', 'password', 'telegram_username', 'patronymic', 'mobile_phone']:
            if field in kwargs and kwargs[field]:
                data[field] = kwargs[field]
        
        # Добавляем уровень доступа для возможности комментирования
        if 'access_level' in kwargs and kwargs['access_level']:
            data['access_level'] = kwargs['access_level']
        elif not kwargs.get('company_id'):  # Для физлиц без компании - минимальные права
            data['access_level'] = []
        
        logger.info(f"Создаем контакт с данными: {data}")
        response = await self._make_request('POST', '/contacts', data)
        return response if response else {}

    async def create_company(self, name: str, inn: str = None, **kwargs) -> Dict:
        """Создать новую компанию"""
        data = {
            'name': name,
        }
        
        # Добавляем ИНН в дополнительные атрибуты если он указан
        if inn:
            data['custom_parameters'] = {
                'inn_company': inn  # Сохраняем ИНН как дополнительный атрибут
            }
        
        # Добавляем другие поля если они переданы
        for field in ['additional_name', 'address', 'phone', 'email', 'comment', 'site']:
            if field in kwargs and kwargs[field]:
                data[field] = kwargs[field]
        
        # CRM 1C ID для интеграции
        if 'crm_1c_id' in kwargs:
            data['crm_1c_id'] = kwargs['crm_1c_id']
        
        logger.info(f"Создаем компанию с данными: {data}")
        response = await self._make_request('POST', '/api/v1/companies', data)
        return response if response else {}
    
    async def update_contact(self, contact_id: int, **kwargs) -> Dict:
        """Обновить контакт (например, привязать к компании)"""
        data = {}
        
        # Добавляем поля для обновления
        for field in ['company_id', 'first_name', 'last_name', 'phone', 'email', 'position']:
            if field in kwargs and kwargs[field] is not None:
                data[field] = kwargs[field]
        
        if not data:
            logger.warning("Нет данных для обновления контакта")
            return {}
        
        logger.info(f"Обновляем контакт {contact_id} с данными: {data}")
        response = await self._make_request('PUT', f'/contacts/{contact_id}', data)
        return response if response else {}

    async def get_companies(self, limit: int = 50) -> List[Dict]:
        """Получить список компаний"""
        try:
            # Используем правильный endpoint согласно документации
            response = await self._make_request(
                'GET', 
                '/api/v1/companies/list',
                params={'page[size]': min(limit, 100)}  # Максимальный размер 100
            )
            
            if not response:
                return []
            
            # Согласно документации, ответ содержит массив companies
            if isinstance(response, dict) and 'companies' in response:
                return response['companies']
            elif isinstance(response, list):
                return response
            
            return []
        except Exception as e:
            logger.error(f"Ошибка получения компаний: {e}")
            return []

    async def search_company_by_inn(self, inn: str) -> Optional[Dict]:
        """Поиск компании по ИНН"""
        try:
            logger.info(f"Ищем компанию с ИНН: {inn}")
            
            # Сначала пробуем поиск через search_string (возможно ИНН указан в названии)
            response = await self._make_request(
                'GET',
                '/api/v1/companies',
                params={'search_string': inn}
            )
            
            if response and 'companies' in response and response['companies']:
                logger.info(f"Найдена компания через поиск по строке: {response['companies'][0].get('name')}")
                return response['companies'][0]
            
            # Получаем список всех компаний для детального поиска
            companies = await self.get_companies(100)
            logger.info(f"Загружено {len(companies)} компаний для поиска")
            
            # Ищем компанию с нужным ИНН
            for company in companies:
                logger.debug(f"Проверяем компанию: {company.get('name')} (ID: {company.get('id')})")
                
                # Проверяем дополнительные атрибуты (custom_parameters)
                custom_params = company.get('custom_parameters', {})
                if custom_params:
                    for param_key, param_value in custom_params.items():
                        param_key_lower = param_key.lower()
                        param_value_str = str(param_value) if param_value else ''
                        
                        # Ищем поля связанные с ИНН
                        if any(inn_field in param_key_lower for inn_field in ['inn', 'инн', 'tax', 'налог']) and param_value_str == inn:
                            logger.info(f"Найдена компания с ИНН {inn} в доп. атрибуте '{param_key}': {company.get('name')}")
                            return company
                
                # Проверяем основные поля компании
                if (company.get('crm_1c_id') == inn or
                    inn in str(company.get('name', '')) or
                    inn in str(company.get('additional_name', ''))):
                    logger.info(f"Найдена компания с ИНН {inn} в основных полях: {company.get('name')}")
                    return company
                
                # Проверяем параметры компании (если они в другом формате)
                parameters = company.get('parameters', [])
                if parameters:
                    for param in parameters:
                        if isinstance(param, dict):
                            param_name = str(param.get('name', '')).lower()
                            param_value = str(param.get('value', ''))
                            
                            if any(inn_field in param_name for inn_field in ['inn', 'инн', 'tax', 'налог']) and param_value == inn:
                                logger.info(f"Найдена компания с ИНН {inn} в параметре {param_name}: {company.get('name')}")
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
