#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import aiohttp
import logging
import base64
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
import config

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OkdeskAPI:
    """Класс для работы с API OkDesk"""
    
    def __init__(self, api_url: str = None, api_token: str = None):
        """Инициализация клиента API"""
        # Нормализация URL
        api_url_raw = api_url or config.OKDESK_API_URL
        self.api_token = api_token or config.OKDESK_API_TOKEN
        
        # Очищаем URL от лишних компонентов
        # Убираем trailing слеши и лишние компоненты пути
        if '://' in api_url_raw:
            protocol, rest = api_url_raw.split('://')
            base_url = protocol + '://' + rest.split('/')[0]
        else:
            base_url = api_url_raw.split('/')[0]
        
        # Формируем базовый URL для API запросов
        self.api_url = f"{base_url}/api/v1/"
        
        # Настройка заголовков для API запросов
        self.headers = {
            'Content-Type': 'application/json'
            # Токен передается через параметры запроса, а не через Authorization
        }
        
        logger.info(f"API URL: {self.api_url}")
    
    async def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Any:
        """Выполняет запрос к API OkDesk и обрабатывает ответ"""
        # Добавляем API токен как параметр запроса
        # Удаляем слеш в начале endpoint, чтобы избежать дублирования слеша
        endpoint_clean = endpoint.lstrip('/')
        if '?' in endpoint_clean:
            url = f"{self.api_url}{endpoint_clean}&api_token={self.api_token}"
        else:
            url = f"{self.api_url}{endpoint_clean}?api_token={self.api_token}"
        
        # Логируем запрос для отладки
        logger.info(f"{method} {url}")
        if data:
            logger.info(f"Request data: {data}")
        
        try:
            async with aiohttp.ClientSession() as session:
                if method == 'GET':
                    async with session.get(url, headers=self.headers) as resp:
                        response_text = await resp.text()
                        
                        # Логируем ответ
                        logger.info(f"Response status: {resp.status}")
                        logger.info(f"Response: {response_text}")
                        
                        if resp.status == 200:
                            try:
                                parsed = json.loads(response_text)
                                logger.info(f"Parsed response: {str(parsed)[:100]}...")
                                return parsed
                            except Exception as e:
                                logger.error(f"Ошибка парсинга JSON: {e}")
                                return None
                        else:
                            logger.error(f"API Error {resp.status}: {response_text}")
                            return None
                
                elif method in ['POST', 'PUT']:
                    json_data = json.dumps(data) if data else None
                    
                    async with session.request(method, url, headers=self.headers, data=json_data) as resp:
                        response_text = await resp.text()
                        
                        # Логируем ответ
                        logger.info(f"Response status: {resp.status}")
                        logger.info(f"Response: {response_text}")
                        
                        if resp.status in [200, 201]:
                            try:
                                parsed = json.loads(response_text)
                                logger.info(f"Parsed response: {str(parsed)[:100]}...")
                                return parsed
                            except Exception as e:
                                logger.error(f"Ошибка парсинга JSON: {e}")
                                if "success" in response_text.lower():
                                    return {"success": True}
                                return None
                        else:
                            logger.error(f"API Error {resp.status}: {response_text}")
                            logger.error(f"Error details: {json.loads(response_text) if response_text else None}")
                            return None
        
        except Exception as e:
            logger.error(f"Ошибка запроса к API: {e}")
            return None
    
    async def get_issues(self, status_ids: List[int] = None, limit: int = 10) -> List[Dict]:
        """Получить список заявок"""
        try:
            # Судя по результатам тестирования, endpoint /issues возвращает 404,
            # поэтому попробуем использовать последовательные запросы к конкретным заявкам
            # Начнем с запроса последних заявок по порядку
            issues = []
            # Пробуем запросить несколько последних заявок
            for issue_id in range(limit, 0, -1):
                try:
                    issue = await self.get_issue(issue_id)
                    if issue and 'errors' not in issue:
                        issues.append(issue)
                        if len(issues) >= limit:
                            break
                except Exception:
                    continue
                    
            return issues
        except Exception as e:
            logger.error(f"Ошибка получения заявок: {e}")
            return []
    
    async def get_issue(self, issue_id: int) -> Dict:
        """Получить заявку по ID"""
        try:
            response = await self._make_request('GET', f'issues/{issue_id}')
            
            # Проверяем, нет ли ошибок в ответе
            if isinstance(response, dict) and 'errors' not in response:
                return response
            elif isinstance(response, dict) and 'errors' in response:
                logger.warning(f"API вернул ошибку для заявки {issue_id}: {response.get('errors')}")
            
            return {}
        except Exception as e:
            logger.error(f"Ошибка получения заявки {issue_id}: {e}")
            return {}
    
    async def create_issue(self, title: str, description: str, **kwargs) -> Dict:
        """Создать новую заявку"""
        # Логируем входные параметры для диагностики
        logger.info(f"📌 Входные параметры create_issue: {kwargs}")
        
        data = {
            'title': title,
            'description': description,
            'type_id': kwargs.get('type_id', 1),  # Тип заявки по умолчанию
            'priority_id': kwargs.get('priority_id', 2),  # Приоритет по умолчанию
            'status_id': kwargs.get('status_id', 1),  # Статус по умолчанию
        }
        
        # Привязываем клиента к заявке по новому формату API Okdesk
        client = {}
        
        # Добавляем контакт, если указан
        if 'contact_id' in kwargs and kwargs['contact_id']:
            client['contact'] = {'id': kwargs['contact_id']}
            logger.info(f"✅ Привязываем контакт к заявке: contact_id = {kwargs['contact_id']}")
        
        # Если указан телефон, но нет contact_id, пытаемся найти контакт по телефону
        elif 'phone' in kwargs and kwargs['phone'] and 'contact_id' not in kwargs:
            contact = await self.find_contact_by_phone(kwargs['phone'])
            if contact and 'id' in contact:
                client['contact'] = {'id': contact['id']}
                logger.info(f"✅ Привязываем контакт по телефону: contact_id = {contact['id']}")
        
        # Добавляем компанию, если указана
        if 'company_id' in kwargs and kwargs['company_id']:
            client['company'] = {'id': kwargs['company_id']}
            logger.info(f"✅ Привязываем компанию к заявке: company_id = {kwargs['company_id']}")
        
        # Добавляем клиента к данным заявки, если есть контакт или компания
        if client:
            data['client'] = client
            logger.info(f"✅ Привязываем клиента к заявке: {client}")
        
        # Для обратной совместимости также оставляем старые параметры
        if 'contact_id' in kwargs:
            data['contact_id'] = kwargs['contact_id']
        if 'company_id' in kwargs:
            data['company_id'] = kwargs['company_id']
        if 'assignee_id' in kwargs:
            data['assignee_id'] = kwargs['assignee_id']
        
        logger.info(f"Создаем заявку с данными: {data}")
        response = await self._make_request('POST', 'issues', data)
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
            author_type: Тип автора (contact, employee, client)
            author_name: Имя автора комментария
            client_phone: Телефон клиента для поиска контакта
            contact_auth_code: Код авторизации контакта
            contact_id: ID контакта (приоритетнее чем поиск по телефону)
        """
        # Если указан contact_id, используем его для автора
        if contact_id:
            author_id = contact_id
            author_type = 'contact'
        
        data = {
            'content': content,
            'public': is_public,
        }
        
        # Если указан код авторизации контакта
        if contact_auth_code:
            endpoint = f"/issues/{issue_id}/contact_comments"
            data['auth_code'] = contact_auth_code
            return await self._contact_comment(endpoint, data)
        
        endpoint = f"/issues/{issue_id}/comments"
        
        logger.info(f"=== СОЗДАНИЕ КОММЕНТАРИЯ ===")
        logger.info(f"issue_id: {issue_id}")
        logger.info(f"author_id: {author_id}")
        logger.info(f"author_type: {author_type}")
        logger.info(f"client_phone: {client_phone}")
        logger.info(f"contact_id: {contact_id}")
        logger.info(f"content: {content[:50]}...")
        
        # author_id и author_type обязательны!
        if author_id and author_type:
            data['author_id'] = author_id
            data['author_type'] = author_type
            logger.info(f"✅ Используем переданные параметры: author_id={author_id}, author_type={author_type}")
        else:
            logger.info(f"⚠️ Не указаны author_id и/или author_type")
            
            # Пытаемся найти контакт по телефону, если предоставлен client_phone
            if client_phone:
                logger.info(f"🔍 Пытаемся найти контакт по телефону: {client_phone}")
                contact = await self.find_contact_by_phone(client_phone)
                
                if contact and 'id' in contact:
                    data['author_id'] = contact['id']
                    data['author_type'] = 'contact'
                    logger.info(f"✅ Используем найденный контакт: author_id={contact['id']}, author_type=contact")
                else:
                    # Если контакт не найден, используем системного пользователя
                    data['author_id'] = 5  # ID Manager
                    data['author_type'] = 'employee'
                    logger.warning(f"⚠️ Контакт не найден. Используем fallback: author_id=5, author_type=employee")
            else:
                # Используем системного пользователя как fallback
                data['author_id'] = 5  # ID Manager из ваших логов
                data['author_type'] = 'employee'
                logger.warning(f"⚠️ Используем fallback: author_id=5, author_type=employee")
        
        if author_name:
            data['author_name'] = author_name
        
        logger.info(f"📤 Отправляем данные: {data}")
        response = await self._make_request('POST', endpoint, data)
        
        # Обработка ответа API
        if response:
            logger.info(f"✅ Ответ API: {response}")
            return response
        else:
            logger.error(f"❌ Не удалось создать комментарий: {response}")
            return {}
    
    async def _contact_comment(self, endpoint: str, data: Dict) -> Dict:
        """Отправить комментарий от имени контакта (требуется auth_code)"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {'Content-Type': 'application/json'}
                
                # Логируем данные запроса
                logger.info(f"Endpoint: {endpoint}")
                logger.info(f"Data: {data}")
                
                async with session.post(
                    urljoin(self.api_url, endpoint),
                    headers=headers,
                    data=json.dumps(data)
                ) as resp:
                    response_text = await resp.text()
                    
                    if resp.status in [200, 201]:
                        try:
                            response = json.loads(response_text)
                            logger.info(f"✅ Комментарий от контакта создан: {response}")
                            return response
                        except:
                            logger.info(f"✅ Комментарий создан от контакта (без JSON ответа)")
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
            
            return []
        except Exception as e:
            logger.error(f"Ошибка получения контактов: {e}")
            return []
    
    async def find_contact_by_phone(self, phone: str) -> Optional[Dict]:
        """Найти контакт по номеру телефона через API (рекомендуемый метод)"""
        if not phone:
            logger.warning("❌ Не указан телефон для поиска контакта")
            return None
            
        try:
            # Очистка телефона от лишних символов для сравнения
            clean_phone = ''.join(c for c in phone if c.isdigit())
            
            if len(clean_phone) < 5:
                logger.warning(f"❌ Некорректный формат телефона: {phone}")
                return None
                
            # Прямой поиск по телефону
            endpoint = f"/contacts?phone={phone}"
            logger.info(f"🔍 Прямой поиск контакта по телефону: {phone}")
            response = await self._make_request('GET', endpoint)
            
            # Проверяем формат ответа и наличие id
            if response and isinstance(response, dict) and 'id' in response:
                logger.info(f"✅ Найден контакт через API: {response.get('name', 'Без имени')} (ID: {response.get('id')})")
                return response
            
            # Если не нашли, пробуем поиск с другим форматом телефона
            # Вариант с 7 в начале
            if clean_phone.startswith('8') and len(clean_phone) == 11:
                alt_phone = '7' + clean_phone[1:]
                endpoint = f"/contacts?phone={alt_phone}"
                logger.info(f"🔍 Поиск с альтернативным форматом телефона: {alt_phone}")
                response = await self._make_request('GET', endpoint)
                
                if response and isinstance(response, dict) and 'id' in response:
                    logger.info(f"✅ Найден контакт через API: {response.get('name', 'Без имени')} (ID: {response.get('id')})")
                    return response
            
            # Если не нашли, попробуем поиск всех контактов и фильтрацию
            logger.info(f"🔍 Поиск контакта среди всех контактов (запасной вариант)")
            endpoint = f"/contacts?limit=100"  # Получаем первые 100 контактов
            response = await self._make_request('GET', endpoint)
            
            if response and isinstance(response, list):
                for contact in response:
                    # Проверяем, содержит ли контакт указанный телефон (с разными форматами)
                    contact_phone = contact.get('phone', '')
                    contact_mobile = contact.get('mobile_phone', '')
                    
                    # Очищаем телефоны контактов для сравнения
                    clean_contact_phone = ''.join(c for c in contact_phone if c.isdigit())
                    clean_contact_mobile = ''.join(c for c in contact_mobile if c.isdigit())
                    
                    # Проверка соответствия по последним цифрам (если телефон длинный)
                    if len(clean_phone) >= 10 and len(clean_contact_phone) >= 10:
                        if clean_phone[-10:] == clean_contact_phone[-10:]:
                            logger.info(f"✅ Найден контакт через сравнение последних цифр: {contact.get('name', 'Без имени')} (ID: {contact.get('id')})")
                            return contact
                    
                    if len(clean_phone) >= 10 and len(clean_contact_mobile) >= 10:
                        if clean_phone[-10:] == clean_contact_mobile[-10:]:
                            logger.info(f"✅ Найден контакт через сравнение последних цифр: {contact.get('name', 'Без имени')} (ID: {contact.get('id')})")
                            return contact
                    
                    # Проверка на наличие одного номера в другом
                    if clean_phone and (clean_phone in clean_contact_phone or clean_phone in clean_contact_mobile):
                        logger.info(f"✅ Найден контакт через поиск: {contact.get('name', 'Без имени')} (ID: {contact.get('id')})")
                        return contact
                    
                    if clean_contact_phone and clean_contact_phone in clean_phone:
                        logger.info(f"✅ Найден контакт через обратный поиск: {contact.get('name', 'Без имени')} (ID: {contact.get('id')})")
                        return contact
                    
                    if clean_contact_mobile and clean_contact_mobile in clean_phone:
                        logger.info(f"✅ Найден контакт через обратный поиск: {contact.get('name', 'Без имени')} (ID: {contact.get('id')})")
                        return contact
            
            logger.info(f"❌ Контакт с телефоном {phone} не найден через API")
            return None
        except Exception as e:
            logger.error(f"Ошибка поиска контакта через API: {e}")
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
        response = await self._make_request('POST', 'contacts', data)
        return response if response else {}
    
    # Добавляем алиас метода для обратной совместимости
    async def search_contact_by_phone(self, phone: str) -> Dict:
        """Алиас метода find_contact_by_phone для обратной совместимости"""
        return await self.find_contact_by_phone(phone)
    
    async def close(self):
        """Метод для закрытия ресурсов (для совместимости)"""
        # В данной реализации нет долгоживущих ресурсов, которые требуется закрывать
        pass
