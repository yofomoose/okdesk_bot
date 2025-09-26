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
    
    async def _make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Any:
        """Выполняет запрос к API OkDesk и обрабатывает ответ"""
        # Добавляем API токен как параметр запроса
        # Удаляем слеш в начале endpoint, чтобы избежать дублирования слеша
        endpoint_clean = endpoint.lstrip('/')
        
        # Подготавливаем параметры
        query_params = params.copy() if params else {}
        if 'api_token' not in query_params:
            query_params['api_token'] = self.api_token
            
        # Формируем URL с параметрами
        if query_params:
            # Обрабатываем специальные параметры массивов (например, company_ids[])
            param_strings = []
            for key, value in query_params.items():
                if key.endswith('[]'):
                    # Для массивов используем специальное форматирование
                    param_strings.append(f"{key}={value}")
                else:
                    param_strings.append(f"{key}={value}")
            
            if '?' in endpoint_clean:
                url = f"{self.api_url}{endpoint_clean}&{'&'.join(param_strings)}"
            else:
                url = f"{self.api_url}{endpoint_clean}?{'&'.join(param_strings)}"
        else:
            url = f"{self.api_url}{endpoint_clean}"
        
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
                            if resp.status == 422:
                                # Для ошибки 422 возвращаем специальный словарь с информацией об ошибке
                                try:
                                    error_data = json.loads(response_text)
                                    return {"error": 422, "details": error_data}
                                except:
                                    return {"error": 422, "details": response_text}
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
            
    async def update_issue(self, issue_id: int, data: Dict) -> Dict:
        """
        Обновить заявку
        
        Args:
            issue_id: ID заявки
            data: Данные для обновления
        
        Returns:
            Dict: Результат обновления или пустой словарь в случае ошибки
        """
        try:
            logger.info(f"Обновление заявки {issue_id} с данными: {data}")
            
            # Отправляем запрос на обновление
            response = await self._make_request('PUT', f'issues/{issue_id}', data)
            
            if response:
                logger.info(f"✅ Заявка {issue_id} успешно обновлена")
                return response
            else:
                logger.error(f"❌ Не удалось обновить заявку {issue_id}")
                return {}
        except Exception as e:
            logger.error(f"Ошибка обновления заявки {issue_id}: {e}")
            return {}
    
    async def create_issue(self, title: str, description: str, **kwargs) -> Dict:
        """Создать новую заявку"""
        # Логируем входные параметры для диагностики
        logger.info(f"📌 Входные параметры create_issue: {kwargs}")
        
        # Получаем phone из kwargs для поиска контакта
        phone = kwargs.get('phone')
        user_telegram_id = kwargs.get('telegram_id')
        full_name = kwargs.get('full_name')
        
        data = {
            'title': title,
            'description': description,
            'type_id': kwargs.get('type_id', 1),  # Тип заявки по умолчанию
            'priority_id': kwargs.get('priority_id', 2),  # Приоритет по умолчанию
            'status_id': kwargs.get('status_id', 1),  # Статус по умолчанию
        }
        
        # Добавляем информацию о Telegram пользователе в описание, если она есть
        if user_telegram_id or full_name:
            telegram_info = "\n\n---\n"
            if full_name:
                telegram_info += f"👤 Имя: {full_name}\n"
            if user_telegram_id:
                telegram_info += f"🆔 Telegram ID: {user_telegram_id}\n"
            if phone:
                telegram_info += f"📱 Телефон: {phone}\n"
            telegram_info += "---"
            
            data['description'] = data['description'] + telegram_info
        
        # Привязываем клиента к заявке по новому формату API Okdesk
        client = {}
        
        # Добавляем контакт, если указан
        if 'contact_id' in kwargs and kwargs['contact_id']:
            client['contact'] = {'id': kwargs['contact_id']}
            logger.info(f"✅ Привязываем контакт к заявке: contact_id = {kwargs['contact_id']}")
        
        # Если указан телефон, но нет contact_id, пытаемся найти контакт по телефону
        elif phone:
            logger.info(f"🔍 Поиск контакта по телефону для привязки к заявке: {phone}")
            contact = await self.find_contact_by_phone(phone)
            if contact and 'id' in contact:
                client['contact'] = {'id': contact['id']}
                logger.info(f"✅ Привязываем контакт по телефону: contact_id = {contact['id']}")
                # Также добавляем его в kwargs для дальнейшего использования
                kwargs['contact_id'] = contact['id']
                logger.info(f"✅ Добавляем contact_id в параметры: {kwargs['contact_id']}")
                
                # Извлекаем токен портала из найденного контакта
                portal_token = contact.get('authentication_code')
                if portal_token:
                    logger.info(f"✅ Получен токен портала для существующего контакта: {portal_token[:10]}...")
                else:
                    logger.warning("⚠️ Токен портала не найден в данных существующего контакта")
                
                # Если предоставлена функция обратного вызова для обновления контакта, вызываем её
                if 'update_contact_callback' in kwargs and callable(kwargs['update_contact_callback']):
                    try:
                        logger.info(f"✅ Вызываем callback для обновления найденного contact_id={contact['id']}")
                        await kwargs['update_contact_callback'](contact['id'])
                    except Exception as e:
                        logger.error(f"❌ Ошибка при вызове update_contact_callback: {e}")
                # Если указан telegram_id, обновляем запись пользователя в базе данных
                elif user_telegram_id:
                    try:
                        from database.crud import UserService
                        user = UserService.get_user_by_telegram_id(user_telegram_id)
                        if user:
                            user.okdesk_contact_id = contact['id']
                            # Сохраняем токен портала, если он получен
                            if portal_token:
                                user.portal_token = portal_token
                                logger.info(f"✅ Сохранен токен портала для пользователя {user_telegram_id}")
                            # Commit changes using SQLAlchemy session
                            from models.database import SessionLocal
                            db_session = SessionLocal()
                            db_session.merge(user)
                            db_session.commit()
                            db_session.close()
                            logger.info(f"✅ Обновлен okdesk_contact_id={contact['id']} для пользователя {user_telegram_id} в базе данных")
                    except Exception as e:
                        logger.error(f"❌ Ошибка при обновлении okdesk_contact_id в базе данных: {e}")
            else:
                # Если контакт не найден, создаем новый
                logger.info(f"❗ Контакт не найден по телефону. Создаем новый контакт.")
                
                # Готовим данные для создания контакта
                contact_data = {
                    'first_name': kwargs.get('first_name', full_name.split()[0] if full_name else 'Пользователь'),
                    'last_name': kwargs.get('last_name', ' '.join(full_name.split()[1:]) if full_name and len(full_name.split()) > 1 else 'Telegram'),
                    'phone': phone,
                    'comment': f"Контакт создан автоматически из Telegram. ID: {user_telegram_id}"
                }
                
                # Если есть компания, привязываем к ней
                if 'company_id' in kwargs and kwargs['company_id']:
                    contact_data['company_id'] = kwargs['company_id']
                
                # Создаем контакт
                new_contact = await self.create_contact(**contact_data)
                
                if new_contact and 'id' in new_contact:
                    client['contact'] = {'id': new_contact['id']}
                    logger.info(f"✅ Привязываем новый контакт к заявке: contact_id = {new_contact['id']}")
                    # Также добавляем его в kwargs для дальнейшего использования
                    kwargs['contact_id'] = new_contact['id']
                    logger.info(f"✅ Добавляем новый contact_id в параметры: {kwargs['contact_id']}")
                    
                    # Извлекаем токен портала из ответа API
                    portal_token = new_contact.get('authentication_code')
                    if portal_token:
                        logger.info(f"✅ Получен токен портала для нового контакта: {portal_token[:10]}...")
                    else:
                        logger.warning("⚠️ Токен портала не найден в ответе API при создании контакта")
                    
                    # Если предоставлена функция обратного вызова для обновления контакта, вызываем её
                    if 'update_contact_callback' in kwargs and callable(kwargs['update_contact_callback']):
                        try:
                            logger.info(f"✅ Вызываем callback для обновления contact_id={new_contact['id']}")
                            await kwargs['update_contact_callback'](new_contact['id'])
                        except Exception as e:
                            logger.error(f"❌ Ошибка при вызове update_contact_callback: {e}")
                    # Если указан telegram_id, обновляем запись пользователя в базе данных
                    elif user_telegram_id:
                        try:
                            from database.crud import UserService
                            user = UserService.get_user_by_telegram_id(user_telegram_id)
                            if user:
                                user.okdesk_contact_id = new_contact['id']
                                # Сохраняем токен портала, если он получен
                                if portal_token:
                                    user.portal_token = portal_token
                                    logger.info(f"✅ Сохранен токен портала для пользователя {user_telegram_id}")
                                # Commit changes using SQLAlchemy session
                                from models.database import SessionLocal
                                db_session = SessionLocal()
                                db_session.merge(user)
                                db_session.commit()
                                db_session.close()
                                logger.info(f"✅ Обновлен okdesk_contact_id={new_contact['id']} для пользователя {user_telegram_id} в базе данных")
                        except Exception as e:
                            logger.error(f"❌ Ошибка при обновлении okdesk_contact_id в базе данных: {e}")
                else:
                    logger.error(f"❌ Не удалось создать контакт: {new_contact}")
        
        # Добавляем компанию, если указана явно
        if 'company_id' in kwargs and kwargs['company_id']:
            client['company'] = {'id': kwargs['company_id']}
            logger.info(f"✅ Привязываем компанию к заявке: company_id = {kwargs['company_id']}")
        # Если компания не указана, но есть ИНН, пытаемся найти компанию по ИНН
        elif 'inn' in kwargs and kwargs['inn']:
            logger.info(f"🔍 Поиск компании по ИНН для привязки к заявке: {kwargs['inn']}")
            company = await self.find_company_by_inn(kwargs['inn'])
            if company and 'id' in company:
                client['company'] = {'id': company['id']}
                logger.info(f"✅ Привязываем компанию по ИНН: company_id = {company['id']}")
                # Также добавляем его в kwargs для дальнейшего использования
                kwargs['company_id'] = company['id']
                logger.info(f"✅ Добавляем company_id в параметры: {kwargs['company_id']}")
                
                # Если есть user_telegram_id, обновляем okdesk_company_id в базе данных
                if user_telegram_id:
                    try:
                        from database.crud import UserService
                        user = UserService.get_user_by_telegram_id(user_telegram_id)
                        if user:
                            user.company_id = company['id']
                            # Commit changes using SQLAlchemy session
                            from models.database import SessionLocal
                            db_session = SessionLocal()
                            db_session.merge(user)
                            db_session.commit()
                            db_session.close()
                            logger.info(f"✅ Обновлен okdesk_company_id={company['id']} для пользователя {user_telegram_id} в базе данных")
                    except Exception as e:
                        logger.error(f"❌ Ошибка при обновлении okdesk_company_id в базе данных: {e}")
        
        # Добавляем клиента к данным заявки всегда, даже если нет контакта или компании
        # Это необходимо, чтобы API правильно обработало запрос
        data['client'] = client
        logger.info(f"✅ Привязываем клиента к заявке: {client}")
        
        # Для обратной совместимости также оставляем старые параметры
        if 'contact_id' in kwargs:
            data['contact_id'] = kwargs['contact_id']
        if 'company_id' in kwargs:
            data['company_id'] = kwargs['company_id']
        if 'assignee_id' in kwargs:
            data['assignee_id'] = kwargs['assignee_id']
        
        # Добавляем явную привязку к пользователю, если у нас есть информация о нем
        logger.info(f"Создаем заявку с данными: {data}")
        response = await self._make_request('POST', 'issues', data)
        
        # Проверяем успешность создания заявки
        if response and 'id' in response:
            issue_id = response['id']
            logger.info(f"✅ Заявка создана успешно: ID={issue_id}")
            
            # Проверяем привязку клиента
            if not client.get('contact') and not client.get('company'):
                logger.warning("⚠️ Заявка создана без привязки к клиенту")
            elif not client.get('contact'):
                logger.warning("⚠️ Заявка привязана только к компании, но не к контакту")
            elif not client.get('company'):
                logger.info("✅ Заявка привязана к контакту (без компании)")
            else:
                logger.info("✅ Заявка привязана к контакту и компании")
        else:
            logger.error(f"❌ Не удалось создать заявку: {response}")
            
        return response if response else {}
    
    async def upload_file(self, file_path: str, file_data: bytes, filename: str = None) -> Optional[Dict]:
        """
        Загрузить файл в Okdesk для дальнейшего прикрепления к заявке или комментарию
        
        Args:
            file_path: Путь к файлу (для определения имени)
            file_data: Данные файла в байтах
            filename: Имя файла (если отличается от file_path)
        
        Returns:
            Dict: Информация о загруженном файле или None в случае ошибки
        """
        try:
            # Определяем имя файла
            if not filename:
                filename = os.path.basename(file_path) if file_path else 'uploaded_file'
            
            logger.info(f"📎 Загружаем файл: {filename} ({len(file_data)} байт)")
            
            # Формируем multipart/form-data запрос
            form_data = aiohttp.FormData()
            form_data.add_field('attachment', file_data, filename=filename)
            form_data.add_field('api_token', self.api_token)
            
            # Загружаем файл
            url = f"{self.api_url}attachments"
            logger.info(f"📎 URL загрузки: {url}")
            
            async with aiohttp.ClientSession() as session:
                logger.info(f"📤 Отправка POST запроса на {url}")
                
                async with session.post(url, data=form_data) as resp:
                    response_text = await resp.text()
                    
                    logger.info(f"📥 Upload response status: {resp.status}")
                    logger.info(f"📄 Upload response headers: {dict(resp.headers)}")
                    logger.info(f"📄 Upload response body: {response_text[:500]}{'...' if len(response_text) > 500 else ''}")
                    
                    if resp.status in [200, 201]:
                        try:
                            response_data = json.loads(response_text)
                            logger.info(f"✅ Файл успешно загружен: {response_data}")
                            return response_data
                        except Exception as e:
                            logger.error(f"❌ Ошибка парсинга ответа загрузки файла: {e}")
                            return None
                    else:
                        logger.error(f"❌ Ошибка загрузки файла: {resp.status} - {response_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке файла: {e}")
            return None

    async def add_comment(self, issue_id: int, content: str, is_public: bool = True, 
                         author_id: int = None, author_type: str = None, 
                         author_name: str = None, client_phone: str = None, 
                         contact_auth_code: str = None, contact_id: int = None,
                         attachments: List[Dict] = None) -> Dict:
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
            attachments: Список вложений [{id: int, filename: str}]
        """
        # Если указан contact_id, используем его для автора
        if contact_id:
            author_id = contact_id
            author_type = 'contact'
        
        data = {
            'content': content,
            'public': is_public,
        }
        
        # Добавляем вложения, если они есть
        if attachments:
            data['attachments'] = attachments
            logger.info(f"📎 Добавляем {len(attachments)} вложений к комментарию")
        
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
            logger.info(f"⚠️ Не указаны author_id и/или author_type - будем искать или создавать контакт")
            
            # Пытаемся найти или создать контакт
            contact_id = None
            
            # Пробуем сначала найти контакт по переданному телефону
            if client_phone:
                logger.info(f"🔍 Пытаемся найти контакт по телефону: {client_phone}")
                contact = await self.find_contact_by_phone(client_phone)
                
                if contact and 'id' in contact:
                    contact_id = contact['id']
                    logger.info(f"✅ Найден контакт по телефону: ID={contact_id}")
            
            # Если контакт не найден по телефону, пытаемся найти по заявке
            if not contact_id:
                logger.info(f"🔍 Пытаемся найти контакт через данные заявки: {issue_id}")
                issue_info = await self.get_issue(issue_id)
                
                if issue_info and 'client' in issue_info and issue_info['client'].get('contact'):
                    contact_id = issue_info['client']['contact'].get('id')
                    if contact_id:
                        logger.info(f"✅ Найден контакт через заявку: ID={contact_id}")
                
                # Получаем информацию о компании для дальнейшего использования
                company_id = None
                if issue_info and 'client' in issue_info and issue_info['client'].get('company'):
                    company_id = issue_info['client']['company'].get('id')
                    logger.info(f"✅ Найдена компания через заявку: ID={company_id}")
            
            # Если все еще не нашли контакт и есть телефон, создаем новый
            if not contact_id and client_phone:
                logger.info(f"❗ Контакт не найден. Создаем новый контакт.")
                
                # Готовим данные для создания контакта
                contact_data = {
                    'first_name': author_name.split()[0] if author_name else 'Пользователь',
                    'last_name': ' '.join(author_name.split()[1:]) if author_name and len(author_name.split()) > 1 else 'Telegram',
                    'phone': client_phone,
                    'comment': f"Контакт создан автоматически из Telegram при добавлении комментария к заявке #{issue_id}"
                }
                
                # Если нашли компанию, привязываем к ней
                if company_id:
                    contact_data['company_id'] = company_id
                
                # Создаем контакт
                new_contact = await self.create_contact(**contact_data)
                
                if new_contact and 'id' in new_contact:
                    contact_id = new_contact['id']
                    logger.info(f"✅ Создан новый контакт: ID={contact_id}")
            
            # Используем найденный или созданный контакт
            if contact_id:
                data['author_id'] = contact_id
                data['author_type'] = 'contact'
                logger.info(f"✅ Используем контакт как автора: author_id={contact_id}, author_type=contact")
            else:
                # Если не удалось найти или создать контакт, используем системного пользователя
                data['author_id'] = 5  # ID Manager из ваших логов
                data['author_type'] = 'employee'
                logger.warning(f"⚠️ Не удалось найти или создать контакт. Используем системного пользователя: author_id=5, author_type=employee")
        
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
            
            # Создаем различные форматы телефона для поиска
            formatted_phones = [phone]  # исходный телефон
            
            # Добавляем версию с + в начале, если его нет
            if not phone.startswith('+'):
                formatted_phones.append(f"+{clean_phone}")
            
            # Преобразования формата для российских номеров
            if len(clean_phone) == 11 and clean_phone.startswith('8'):
                formatted_phones.append(f"+7{clean_phone[1:]}")
                formatted_phones.append(f"7{clean_phone[1:]}")
            elif len(clean_phone) == 11 and clean_phone.startswith('7'):
                formatted_phones.append(f"+{clean_phone}")
                formatted_phones.append(f"8{clean_phone[1:]}")
            elif len(clean_phone) == 10:  # если номер без кода страны
                formatted_phones.append(f"+7{clean_phone}")
                formatted_phones.append(f"7{clean_phone}")
                formatted_phones.append(f"8{clean_phone}")
            
            logger.info(f"🔍 Варианты телефонов для поиска: {formatted_phones}")
            
            # Пробуем каждый формат телефона для поиска
            for formatted_phone in formatted_phones:
                endpoint = f"/contacts?phone={formatted_phone}"
                logger.info(f"🔍 Поиск контакта по телефону: {formatted_phone}")
                response = await self._make_request('GET', endpoint)
            
            # Проверяем формат ответа и наличие id
            if response and isinstance(response, dict) and 'id' in response:
                logger.info(f"✅ Найден контакт через API: {response.get('name', 'Без имени')} (ID: {response.get('id')})")
                
                # Если есть телефон, попробуем найти пользователя в базе и обновить его okdesk_contact_id
                try:
                    from database.crud import UserService
                    from models.database import SessionLocal, User

                    clean_search_phone = ''.join(c for c in phone if c.isdigit())

                    # Получаем пользователей без okdesk_contact_id
                    db_session = SessionLocal()
                    users = db_session.query(User).filter(User.okdesk_contact_id.is_(None), User.phone.isnot(None)).all()

                    for user in users:
                        if user.phone:
                            clean_user_phone = ''.join(c for c in user.phone if c.isdigit())
                            # Сравниваем последние 10 цифр телефонов
                            if (len(clean_search_phone) >= 10 and len(clean_user_phone) >= 10 and
                                clean_search_phone[-10:] == clean_user_phone[-10:]):
                                # Обновляем okdesk_contact_id для пользователя
                                user.okdesk_contact_id = response['id']
                                db_session.merge(user)
                                db_session.commit()
                                logger.info(f"✅ Обновлен okdesk_contact_id={response['id']} для пользователя {user.telegram_id} в базе данных")

                    db_session.close()
                except Exception as e:
                    logger.error(f"❌ Ошибка при обновлении okdesk_contact_id в базе данных: {e}")
                
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
    
    async def find_contact_by_telegram_username(self, telegram_username: str) -> Optional[Dict]:
        """
        Найти контакт по Telegram username
        
        Args:
            telegram_username: Telegram username для поиска
            
        Returns:
            Dict: Данные контакта или None если не найден
        """
        try:
            logger.info(f"🔍 Поиск контакта по Telegram username: {telegram_username}")
            
            # Пробуем поиск через API с фильтром
            endpoint = f"/contacts?telegram_username={telegram_username}"
            response = await self._make_request('GET', endpoint)
            
            if response and isinstance(response, list) and len(response) > 0:
                contact = response[0]  # Берем первый найденный контакт
                logger.info(f"✅ Найден контакт через API: {contact.get('name', 'Без имени')} (ID: {contact.get('id')})")
                return contact
            
            # Если не нашли, попробуем поиск всех контактов и фильтрацию
            logger.info(f"🔍 Поиск контакта среди всех контактов (запасной вариант)")
            endpoint = f"/contacts?limit=100"  # Получаем первые 100 контактов
            response = await self._make_request('GET', endpoint)
            
            if response and isinstance(response, list):
                for contact in response:
                    # Проверяем telegram_username в контакте
                    contact_telegram = contact.get('telegram_username', '')
                    if contact_telegram == telegram_username:
                        logger.info(f"✅ Найден контакт через фильтрацию: {contact.get('name', 'Без имени')} (ID: {contact.get('id')})")
                        return contact
            
            logger.info(f"❌ Контакт с Telegram username {telegram_username} не найден через API")
            return None
        except Exception as e:
            logger.error(f"Ошибка поиска контакта по Telegram username: {e}")
            return None
    
    async def create_contact(self, first_name: str, last_name: str, **kwargs) -> Dict:
        """Создать новый контакт"""
        data = {
            'first_name': first_name,
            'last_name': last_name
        }
        
        # Добавляем дополнительные поля согласно документации API
        for field in ['patronymic', 'telegram_username', 'phone', 'email', 'company_id', 'position', 'comment', 'maintenance_entity_ids']:
            if field in kwargs and kwargs[field]:
                data[field] = kwargs[field]
                if field == 'telegram_username':
                    logger.info(f"Добавляем Telegram username: {kwargs[field]}")
                if field == 'maintenance_entity_ids':
                    logger.info(f"Добавляем объекты обслуживания: {kwargs[field]}")
        
        # Примечание: ИНН не добавляем как параметр контакта, так как такой параметр не существует в OkDesk
        # ИНН должен указываться в comment или связываться через company_id
        if 'inn_company' in kwargs and kwargs['inn_company']:
            inn = kwargs['inn_company']
            logger.info(f"ИНН {inn} будет указан в комментарии, а не как отдельный параметр контакта")
            # ИНН уже должен быть указан в comment при вызове этого метода
        
        logger.info(f"Создаем контакт с данными: {data}")
        response = await self._make_request('POST', 'contacts', data)
        
        # Если получили ошибку 422, возвращаем её для обработки выше
        if response and isinstance(response, dict) and response.get('error') == 422:
            return response
        
        return response if response else {}
    
    async def get_contact_portal_token(self, contact_id: int) -> Optional[str]:
        """Получить токен портала для контакта"""
        try:
            logger.info(f"Получаем токен портала для контакта ID={contact_id}")
            response = await self._make_request('GET', f'contacts/{contact_id}')
            
            if response and isinstance(response, dict):
                auth_code = response.get('authentication_code')
                if auth_code:
                    logger.info(f"✅ Найден токен портала для контакта {contact_id}")
                    return auth_code
                else:
                    logger.warning(f"⚠️ Токен портала не найден для контакта {contact_id}")
                    return None
            else:
                logger.error(f"❌ Не удалось получить данные контакта {contact_id}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка получения токена портала для контакта {contact_id}: {e}")
            return None
    
    async def create_company(self, name: str, inn: str = None, **kwargs) -> Dict:
        """
        Создать новую компанию
        
        Args:
            name: Название компании
            inn: ИНН компании
            **kwargs: Дополнительные параметры (phone, email, etc)
        
        Returns:
            Dict: Данные созданной компании или пустой словарь в случае ошибки
        """
        data = {
            'name': name
        }
        
        # Добавляем ИНН, если он указан
        if inn and inn.strip():
            # Попробуем разные варианты передачи ИНН
            
            # Вариант 1: Как custom_parameters
            if 'custom_parameters' not in data:
                data['custom_parameters'] = {}
            data['custom_parameters']['inn_company'] = inn.strip()
            data['custom_parameters']['ИНН Компании'] = inn.strip()
            
            # Вариант 2: В корне запроса
            data['inn_company'] = inn.strip()
            data['ИНН Компании'] = inn.strip()
            
            # Вариант 3: Как parameters (массив объектов)
            if 'parameters' not in data:
                data['parameters'] = []
            
            data['parameters'].append({
                'code': 'inn_company',
                'name': 'ИНН Компании',
                'value': inn.strip()
            })
            
            # Дополнительный вариант с другими названиями полей
            data['parameters'].append({
                'code': 'INN',
                'name': 'ИНН',
                'value': inn.strip()
            })
            
            # Еще вариант для поля inn
            data['inn'] = inn.strip()
        
        # Добавляем дополнительные поля
        for field in ['phone', 'email', 'address', 'type_id', 'web_site', 'comment']:
            if field in kwargs and kwargs[field]:
                data[field] = kwargs[field]
        
        logger.info(f"Создаем компанию с данными: {data}")
        response = await self._make_request('POST', 'companies', data)
        
        if response and 'id' in response:
            logger.info(f"✅ Компания создана успешно: ID={response['id']}, Название={response.get('name', 'Без названия')}")
            
            # Если компания создана с ИНН, обновим базу данных пользователей
            if inn:
                try:
                    from models.database import SessionLocal, User

                    db_session = SessionLocal()

                    # Получаем пользователей с этим ИНН, у которых не задан company_id
                    users = db_session.query(User).filter(User.inn_company == inn, User.company_id.is_(None)).all()

                    for user in users:
                        # Обновляем company_id для пользователя
                        user.company_id = response['id']
                        db_session.merge(user)
                        db_session.commit()
                        logger.info(f"✅ Обновлен company_id={response['id']} для пользователя {user.telegram_id} в базе данных")

                    db_session.close()
                except Exception as e:
                    logger.error(f"❌ Ошибка при обновлении company_id в базе данных: {e}")
                    
        return response if response else {}
    
    async def find_company_by_inn(self, inn: str, create_if_not_found: bool = False) -> Optional[Dict]:
        """
        Найти компанию по ИНН и сохранить её ID в базе данных для соответствующих пользователей.
        
        Args:
            inn: ИНН компании для поиска
            create_if_not_found: Создавать компанию, если не найдена (по умолчанию False)
        
        Returns:
            Dict: Данные компании или None, если не найдена
        """""
        try:
            if not inn or not inn.strip():
                logger.warning("❌ ИНН не указан для поиска компании")
                return None
            
            # Очищаем ИНН от лишних символов
            clean_inn = ''.join(c for c in inn if c.isdigit())
            
            if not clean_inn:
                logger.warning(f"❌ ИНН '{inn}' не содержит цифр после очистки")
                return None
            
            logger.info(f"🔍 Поиск компании по ИНН: {clean_inn}")
            
            # Пробуем несколько способов поиска компании по ИНН
            logger.info(f"🔍 Выполняем поиск компании через API по custom_parameters[inn_company]={clean_inn}...")
            
            # Вариант 1: Поиск через custom_parameters для inn_company
            companies = await self._make_request('GET', f"companies/list?custom_parameters[inn_company]={clean_inn}")
            
            if not companies or not isinstance(companies, list):
                logger.info(f"🔍 Поиск по custom_parameters[inn_company] не дал результатов, пробуем custom_parameters[0001]={clean_inn}...")
                # Вариант 2: Поиск через custom_parameters для кода 0001
                companies = await self._make_request('GET', f"companies/list?custom_parameters[0001]={clean_inn}")
            
            if not companies or not isinstance(companies, list):
                logger.info(f"🔍 Поиск по custom_parameters не дал результатов, пробуем старый метод parameter[inn_company]={clean_inn}...")
                # Вариант 3: Старый метод (может работать в некоторых версиях API)
                companies = await self._make_request('GET', f"companies/list?parameter[inn_company]={clean_inn}")
            
            # Переменная для найденной компании
            company = None
            
            # Проверяем результаты поиска
            if isinstance(companies, list) and companies:
                logger.info(f"✅ Найдено {len(companies)} компаний по запросу inn_company={clean_inn}")
                # Ищем компанию с точным совпадением ИНН
                for comp in companies:
                    # Проверяем ИНН в параметрах компании
                    if 'parameters' in comp:
                        for param in comp.get('parameters', []):
                            # Проверяем разные коды параметров ИНН
                            if param.get('code') in ['inn_company', '0001', 'INN', 'ИНН'] and str(param.get('value', '')).strip() == clean_inn:
                                company = comp
                                logger.info(f"✅ Найдена компания с точным совпадением ИНН {clean_inn}: {company.get('name', 'Без названия')} (ID: {company.get('id')})")
                                break
                    if company:
                        break
                
                # Если не найдено точное совпадение, логируем это
                if not company:
                    logger.warning(f"⚠️ Среди {len(companies)} найденных компаний нет ни одной с точным ИНН {clean_inn}")
                    # Для отладки покажем ИНН первых нескольких компаний
                    for i, comp in enumerate(companies[:5]):
                        comp_inns = []
                        if 'parameters' in comp:
                            for param in comp.get('parameters', []):
                                if param.get('code') in ['inn_company', '0001', 'INN', 'ИНН']:
                                    comp_inns.append(f"{param.get('code')}={param.get('value')}")
                        logger.info(f"Компания {i+1}: {comp.get('name')} (ID: {comp.get('id')}) - ИНН: {', '.join(comp_inns) if comp_inns else 'не указан'}")
            else:
                logger.info(f"❌ Компании с inn_company={clean_inn} не найдены через прямой API-запрос")
                
                # Запасной вариант: получаем и проверяем список всех компаний
                logger.info("🔍 Применяем запасной вариант поиска среди всех компаний...")
                
                companies = await self.get_companies(limit=1000)
                
                if isinstance(companies, list):
                    logger.info(f"🔍 Получено {len(companies)} компаний для проверки")
                    
                    for comp in companies:
                        # Логируем данные компании для отладки
                        logger.debug(f"Проверяем компанию ID: {comp.get('id')}, Название: {comp.get('name')}")
                        
                        # 1. Проверяем ИНН в основных полях
                        inn_values = [
                            str(comp.get('inn', '')).strip(),
                            str(comp.get('inn_company', '')).strip(),
                            str(comp.get('legal_inn', '')).strip()
                        ]
                        
                        if clean_inn in inn_values:
                            company = comp
                            logger.info(f"✅ Найдена компания по основному полю ИНН: {company.get('name', 'Без названия')} (ID: {company.get('id')})")
                            break
                        
                        # 2. Проверяем ИНН в дополнительных параметрах
                        if 'parameters' in comp:
                            found_in_params = False
                            for param in comp.get('parameters', []):
                                if param.get('code') in ['inn', 'INN', 'ИНН', 'inn_company', '0001'] and str(param.get('value', '')).strip() == clean_inn:
                                    company = comp
                                    logger.info(f"✅ Найдена компания по параметру {param.get('code')}: {company.get('name', 'Без названия')} (ID: {company.get('id')})")
                                    found_in_params = True
                                    break
                            
                            if found_in_params:
                                break
                        
                        # 3. Проверяем в custom_parameters, если они есть
                        if 'custom_parameters' in comp:
                            custom_params = comp.get('custom_parameters', {})
                            inn_fields = ['inn', 'INN', 'ИНН', 'inn_company']
                            
                            for field in inn_fields:
                                if field in custom_params and str(custom_params[field]).strip() == clean_inn:
                                    company = comp
                                    logger.info(f"✅ Найдена компания по custom_parameters.{field}: {company.get('name', 'Без названия')} (ID: {company.get('id')})")
                                    break
            
            # Если нашли компанию, обновим связи в базе данных
            if company:
                logger.info(f"✅ Компания найдена: {company.get('name', 'Без названия')} (ID: {company.get('id')})")
                
                # Если найдена компания, обновим её ID для всех пользователей с этим ИНН
                try:
                    from models.database import SessionLocal, User

                    db_session = SessionLocal()

                    # Получаем пользователей с этим ИНН, у которых не задан company_id
                    users = db_session.query(User).filter(User.inn_company == clean_inn, User.company_id.is_(None)).all()

                    for user in users:
                        # Обновляем company_id для пользователя
                        user.company_id = company['id']
                        db_session.merge(user)
                        db_session.commit()
                        logger.info(f"✅ Обновлен company_id={company['id']} для пользователя {user.telegram_id} в базе данных")

                    db_session.close()
                except Exception as e:
                    logger.error(f"❌ Ошибка при обновлении company_id в базе данных: {e}")
                
                return company
            
            logger.info(f"❌ Компания с ИНН {inn} не найдена через API")
            
            # Если компания не найдена, но установлен флаг create_if_not_found, создаем новую компанию
            if create_if_not_found:
                logger.info(f"🔍 Компания с ИНН {inn} не найдена. Создаем новую компанию.")
                
                # Определяем название компании на основе ИНН
                company_name = f"ИП/ООО с ИНН {inn}"
                
                # Создаем новую компанию
                new_company = await self.create_company(
                    name=company_name, 
                    inn=inn,
                    comment=f"Компания создана автоматически из Telegram бота по ИНН {inn}"
                )
                
                if new_company and 'id' in new_company:
                    logger.info(f"✅ Создана новая компания: {new_company.get('name')} (ID: {new_company['id']})")
                    return new_company
                else:
                    logger.error(f"❌ Не удалось создать компанию с ИНН {inn}")
            
            return None
        except Exception as e:
            logger.error(f"Ошибка поиска/создания компании через API: {e}")
            return None
    
    # Добавляем алиас метода для обратной совместимости
    async def search_company_by_inn(self, inn: str) -> Optional[Dict]:
        """Алиас метода find_company_by_inn для обратной совместимости"""
        return await self.find_company_by_inn(inn)
    
    async def get_companies(self, limit: int = 100) -> List[Dict]:
        """
        Получить список компаний с детальной информацией.
        
        Args:
            limit: Ограничение на количество компаний (по умолчанию 100)
        
        Returns:
            List[Dict]: Список словарей с данными компаний
        """
        try:
            logger.info(f"Получаем список компаний (лимит: {limit})...")
            
            # Запрашиваем список всех компаний
            all_companies_response = await self._make_request('GET', f"/companies?per_page={limit}")
            
            if not all_companies_response or not isinstance(all_companies_response, list):
                logger.warning(f"Не удалось получить список компаний или получен пустой список")
                # Если API вернул пустой ответ, проверяем структуру с типом по умолчанию
                return []
            
            # Получаем детальную информацию для каждой компании
            companies_with_details = []
            for company in all_companies_response:
                if 'id' in company:
                    company_id = company['id']
                    # Запрашиваем детали по каждой компании
                    company_details = await self._make_request('GET', f"/companies/{company_id}")
                    if company_details:
                        companies_with_details.append(company_details)
                    else:
                        # Если не удалось получить детали, добавляем базовую информацию
                        companies_with_details.append(company)
            
            logger.info(f"Успешно получено {len(companies_with_details)} компаний с детальной информацией")
            return companies_with_details
        
        except Exception as e:
            logger.error(f"Ошибка при получении списка компаний: {e}")
            return []
    
    async def create_comment(self, issue_id: int, content: str, contact_id: int = None, phone: str = None, 
                        is_public: bool = True, full_name: str = None, telegram_id: str = None) -> Dict:
        """
        Создать комментарий к заявке с автоматической привязкой автора
        
        Args:
            issue_id: ID заявки
            content: Текст комментария
            contact_id: ID контакта в Okdesk (имеет приоритет над phone)
            phone: Телефон для поиска контакта
            is_public: Публичный комментарий (по умолчанию True)
            full_name: Полное имя пользователя (для создания контакта при необходимости)
            telegram_id: Telegram ID пользователя (для создания контакта при необходимости)
        
        Returns:
            Dict: Данные созданного комментария
        """
        # Определяем автора комментария
        author_id = None
        author_type = None
        
        # Если указан contact_id, используем его
        if contact_id:
            author_id = contact_id
            author_type = 'contact'
            logger.info(f"✅ Используем указанный contact_id={contact_id} в качестве автора комментария")
        
        # Если contact_id не указан, но указан телефон, ищем контакт по телефону
        elif phone:
            contact = await self.find_contact_by_phone(phone)
            if contact and 'id' in contact:
                author_id = contact['id']
                author_type = 'contact'
                logger.info(f"✅ Нашли контакт по телефону: id={contact['id']}, name={contact.get('name')}")
            else:
                # Если контакт не найден, пробуем получить информацию о заявке
                issue_info = await self.get_issue(issue_id)
                company_id = None
                
                # Проверяем, привязана ли заявка к компании
                if issue_info and 'client' in issue_info and issue_info['client'].get('company'):
                    company_id = issue_info['client']['company'].get('id')
                    logger.info(f"✅ Нашли компанию для создания контакта: {company_id}")
                
                # Подготавливаем данные для создания контакта
                first_name = full_name.split()[0] if full_name and ' ' in full_name else 'Пользователь'
                last_name = ' '.join(full_name.split()[1:]) if full_name and len(full_name.split()) > 1 else 'Telegram'
                
                contact_data = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'phone': phone,
                    'comment': f"Создан автоматически из Telegram для комментирования заявки #{issue_id}. Telegram ID: {telegram_id}"
                }
                
                # Привязываем к компании, если она найдена
                if company_id:
                    contact_data['company_id'] = company_id
                
                logger.info(f"🔧 Создаем новый контакт с данными: {contact_data}")
                new_contact = await self.create_contact(**contact_data)
                
                if new_contact and 'id' in new_contact:
                    author_id = new_contact['id']
                    author_type = 'contact'
                    logger.info(f"✅ Создан новый контакт: id={new_contact['id']}, name={new_contact.get('name')}")
                else:
                    logger.warning(f"⚠️ Не удалось создать контакт: {new_contact}")
        
        # Вызываем основной метод add_comment с нужными параметрами
        return await self.add_comment(
            issue_id=issue_id,
            content=content,
            is_public=is_public,
            author_id=author_id,
            author_type=author_type,
            author_name=full_name,
            client_phone=phone if not contact_id else None
        )
    
    async def close(self):
        """Метод для закрытия ресурсов (для совместимости)"""
        # В данной реализации нет долгоживущих ресурсов, которые требуется закрывать
        pass
    
    async def rate_issue(self, issue_id: int, rating: int, comment: str = None) -> Dict:
        """Оценить заявку
        
        Args:
            issue_id: ID заявки в Okdesk
            rating: Оценка от 1 до 5
            comment: Комментарий к оценке (опционально)
        
        Returns:
            Dict: Ответ от API с информацией о сохранении оценки
        """
        if not 1 <= rating <= 5:
            raise ValueError("Оценка должна быть от 1 до 5")
        
        logger.info(f"⭐ Начинаем процесс оценки заявки {issue_id} - {rating}/5 звезд")
        
        # Создаем понятный комментарий с оценкой
        rating_comment = f"⭐ ОЦЕНКА: {rating}/5 звезд"
        if comment and comment.strip():
            rating_comment += f"\n💬 Комментарий: {comment.strip()}"
        
        rating_comment += "\n\n_Оценка получена через Telegram бот_"
        
        logger.info(f"📝 Сохраняем оценку через комментарий: {rating_comment[:100]}...")
        
        # Сохраняем оценку через комментарий (единственный рабочий способ)
        response = await self.add_comment(issue_id, rating_comment)
        
        if response:
            logger.info(f"✅ Оценка {rating}/5 успешно сохранена через комментарий в заявке {issue_id}")
            return {
                'success': True,
                'method': 'comment',
                'rating': rating,
                'comment': comment,
                'issue_id': issue_id,
                'message': f'Оценка {rating}/5 сохранена через комментарий'
            }
        else:
            logger.error(f"❌ Не удалось сохранить оценку через комментарий для заявки {issue_id}")
            return {
                'success': False,
                'method': 'comment',
                'rating': rating,
                'issue_id': issue_id,
                'error': 'Не удалось добавить комментарий с оценкой'
            }

    async def create_login_link(self, user_type: str, user_id: int, redirect_url: str = None, expire_minutes: int = 60*24*30, one_time: bool = False) -> Dict:
        """
        Создает ссылку для входа в портал OkDesk
        
        Args:
            user_type: Тип пользователя ('contact' для контактов, 'employee' для сотрудников)
            user_id: ID пользователя
            redirect_url: URL для перенаправления после входа
            expire_minutes: Время жизни ссылки в минутах
            one_time: Одноразовая ли ссылка
            
        Returns:
            Dict: Ответ API с ссылкой для входа
        """
        try:
            data = {
                'user_type': user_type,
                'user_id': user_id,
                'expire_after': expire_minutes,
                'one_time': one_time
            }
            
            logger.info(f"Создаем ссылку входа для {user_type} ID={user_id}")
            response = await self._make_request('POST', 'login_link', data)
            
            if response and 'url' in response:
                logger.info(f"✅ Создана ссылка входа: {response['url']}")
                return response
            else:
                logger.error(f"❌ Не удалось создать ссылку входа: {response}")
                return {}
                
        except Exception as e:
            logger.error(f"Ошибка создания ссылки входа: {e}")
            return {}

    async def create_contact_with_portal_access(self, first_name: str, last_name: str, **kwargs) -> Dict:
        """
        Создает контакт с доступом к клиентскому порталу
        
        Args:
            first_name: Имя контакта
            last_name: Фамилия контакта
            **kwargs: Дополнительные параметры для контакта
            
        Returns:
            Dict: Данные созданного контакта с информацией о доступе к порталу
        """
        # Добавляем права доступа к порталу
        if 'access_level' not in kwargs:
            kwargs['access_level'] = [
                'company_issues',  # Отображать заявки компании
                'allow_close_company_issues'  # Разрешить закрывать заявки компании
            ]
        
        # Создаем случайный логин и пароль, если не указаны
        if 'login' not in kwargs:
            import uuid
            kwargs['login'] = f"user_{str(uuid.uuid4())[:8]}"
        
        if 'password' not in kwargs:
            import secrets
            import string
            alphabet = string.ascii_letters + string.digits
            kwargs['password'] = ''.join(secrets.choice(alphabet) for i in range(12))
        
        logger.info(f"Создаем контакт с доступом к порталу: {first_name} {last_name}")
        response = await self.create_contact(first_name, last_name, **kwargs)
        
        # Если контакт не создан из-за ошибки 422 (уже существует), попробуем найти существующий
        if (not response or (isinstance(response, dict) and response.get('error') == 422)) and 'telegram_username' in kwargs:
            telegram_username = kwargs['telegram_username']
            logger.warning(f"⚠️ Контакт не создан, возможно telegram_username '{telegram_username}' уже существует. Ищем существующий контакт...")
            
            existing_contact = await self.find_contact_by_telegram_username(telegram_username)
            if existing_contact:
                logger.info(f"✅ Найден существующий контакт с ID={existing_contact['id']}")
                response = existing_contact
                
                # Добавляем информацию о логине для существующего контакта
                # (пароль не возвращаем, так как он уже установлен)
                response['portal_login'] = f"existing_user_{existing_contact['id']}"
                response['portal_password'] = "USE_EXISTING_PASSWORD"
            else:
                logger.error(f"❌ Не удалось найти существующий контакт с telegram_username '{telegram_username}'")
                # Возвращаем ошибку 422 если контакт не найден
                if isinstance(response, dict) and response.get('error') == 422:
                    return response
        
        if response and 'id' in response:
            logger.info(f"✅ Контакт готов с ID={response['id']} и доступом к порталу")
            
            # Добавляем информацию о логине для новых контактов
            if 'portal_login' not in response:
                response['portal_login'] = kwargs['login']
                response['portal_password'] = kwargs['password']
        
        return response

    async def get_maintenance_entities(self, company_id: int = None, name: str = None, search_string: str = None) -> List[Dict]:
        """
        Получить список объектов обслуживания с возможностью фильтрации
        
        Args:
            company_id: ID компании для фильтрации (если поддерживается API)
            name: Точное название объекта для поиска
            search_string: Подстрока для поиска в названии или комментарии
        
        Returns:
            List[Dict]: Список объектов обслуживания
        """
        try:
            # Формируем параметры запроса
            params = []
            
            if name:
                params.append(f"name={name}")
            
            if search_string:
                params.append(f"search_string={search_string}")
                
            # Формируем endpoint с параметрами
            endpoint = "maintenance_entities"
            if params:
                endpoint += "?" + "&".join(params)
            
            logger.info(f"🔍 Запрос объектов обслуживания: {endpoint}")
            
            # Выполняем запрос
            response = await self._make_request('GET', endpoint)
            
            if response and isinstance(response, list):
                logger.info(f"✅ Получено {len(response)} объектов обслуживания")
                
                # Если указан company_id, фильтруем результат (может не работать в API, фильтруем локально)
                if company_id:
                    filtered_objects = []
                    for obj in response:
                        # Проверяем привязку к компании (структура может варьироваться)
                        obj_company_id = obj.get('company_id') or obj.get('company', {}).get('id')
                        if obj_company_id == company_id:
                            filtered_objects.append(obj)
                    
                    logger.info(f"🔍 После фильтрации по company_id={company_id}: {len(filtered_objects)} объектов")
                    return filtered_objects
                    
                return response
            else:
                logger.warning("⚠️ Не удалось получить объекты обслуживания или ответ не является списком")
                return []
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения объектов обслуживания: {e}")
            return []

    async def get_maintenance_entities_by_list(self, limit: int = 1000) -> List[Dict]:
        """
        Получить список объектов обслуживания через альтернативный endpoint
        """
        try:
            endpoint = f"maintenance_entities/list?limit={limit}"
            logger.info(f"🔍 Альтернативный запрос объектов обслуживания: {endpoint}")
            
            response = await self._make_request('GET', endpoint)
            
            if response and isinstance(response, list):
                logger.info(f"✅ Получено {len(response)} объектов через maintenance_entities/list")
                return response
            else:
                logger.warning("⚠️ maintenance_entities/list не вернул данных")
                return []
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения объектов через maintenance_entities/list: {e}")
            return []

    async def search_maintenance_entities_by_company(self, company_id: int) -> List[Dict]:
        """
        Поиск объектов обслуживания конкретной компании через разные методы
        """
        try:
            # Метод 1: Прямой поиск по company_id (если поддерживается)
            endpoint = f"maintenance_entities?company_id={company_id}"
            logger.info(f"🔍 Поиск объектов для компании: {endpoint}")
            
            response = await self._make_request('GET', endpoint)
            
            if response and isinstance(response, list) and response:
                logger.info(f"✅ Найдено {len(response)} объектов через company_id")
                return response
            
            # Метод 2: Поиск через дополнительные параметры
            alternative_endpoints = [
                f"maintenance_entities/list?company_id={company_id}",
                f"maintenance_entities?filter[company_id]={company_id}",
                f"companies/{company_id}/maintenance_entities"
            ]
            
            for endpoint in alternative_endpoints:
                logger.info(f"🔍 Пробуем альтернативный endpoint: {endpoint}")
                response = await self._make_request('GET', endpoint)
                
                if response and isinstance(response, list) and response:
                    logger.info(f"✅ Найдено {len(response)} объектов через {endpoint}")
                    return response
            
            logger.warning(f"⚠️ Не удалось найти объекты обслуживания для компании {company_id} через API")
            return []
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска объектов обслуживания для компании: {e}")
            return []

    async def get_maintenance_entities_for_company(self, company_id: int) -> List[Dict]:
        """
        Получить объекты обслуживания для конкретной компании.
        Использует официальный параметр company_ids[] из API документации.
        
        Args:
            company_id: ID компании
            
        Returns:
            List[Dict]: Список объектов обслуживания для компании
        """
        try:
            logger.info(f"🔍 Поиск объектов обслуживания для компании ID={company_id}")
            
            # Метод 1: Официальный способ с параметром company_ids[]
            try:
                params = {
                    'api_token': self.api_token,
                    f'company_ids[]': company_id,  # Официальный параметр из документации
                    'page[size]': 100  # Максимальный размер страницы
                }
                
                logger.info(f"📡 Запрос maintenance_entities/list с company_ids[]={company_id}")
                
                response_data = await self._make_request('GET', 'maintenance_entities/list', params=params)
                
                if response_data:
                    # API возвращает прямой массив объектов, не в wrapper'е
                    entities = response_data if isinstance(response_data, list) else response_data.get('maintenance_entities', [])
                    
                    if entities:
                        logger.info(f"✅ Официальный метод: найдено {len(entities)} объектов")
                        for entity in entities:
                            logger.info(f"  - {entity.get('name', 'Без названия')} (ID: {entity.get('id')})")
                        return entities
                    else:
                        logger.info(f"❌ Официальный метод: нет объектов для компании {company_id}")
                else:
                    logger.warning(f"⚠️ Официальный метод: пустой ответ")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка в официальном методе: {e}")
                
            # Метод 2: Fallback - получаем все объекты и фильтруем на клиенте
            try:
                logger.info(f"🔄 Fallback: получение всех объектов с клиентской фильтрацией")
                
                params = {
                    'api_token': self.api_token,
                    'page[size]': 100
                }
                
                response_data = await self._make_request('GET', 'maintenance_entities/list', params=params)
                
                if response_data:
                    # API возвращает прямой массив объектов, не в wrapper'е
                    all_entities = response_data if isinstance(response_data, list) else response_data.get('maintenance_entities', [])
                    
                    logger.info(f"📋 Fallback: получено {len(all_entities)} всего объектов")
                    
                    # Фильтруем по company_id на стороне клиента
                    company_entities = []
                    for entity in all_entities:
                        entity_company_id = entity.get('company_id')
                        if entity_company_id == company_id:
                            company_entities.append(entity)
                            logger.info(f"  ✓ Найден: {entity.get('name', 'Без названия')} (ID: {entity.get('id')})")
                    
                    if company_entities:
                        logger.info(f"✅ Fallback: найдено {len(company_entities)} объектов")
                        return company_entities
                    else:
                        logger.info(f"❌ Fallback: нет объектов для компании {company_id}")
                else:
                    logger.warning(f"⚠️ Fallback: пустой ответ")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка в fallback методе: {e}")
                
            # Метод 3: Поиск через заявки компании
            try:
                logger.info(f"� Поиск через заявки компании")
                
                # Получаем заявки компании
                params = {
                    'api_token': self.api_token,
                    'company_id': company_id,
                    'page[size]': 50
                }
                
                response_data = await self._make_request('GET', 'issues/list', params=params)
                
                if response_data:
                    # API возвращает прямой массив заявок, не в wrapper'е
                    issues = response_data if isinstance(response_data, list) else response_data.get('issues', [])
                    logger.info(f"📋 Через заявки: найдено {len(issues)} заявок")
                    
                    # Извлекаем уникальные maintenance_entity из заявок
                    maintenance_entities = {}
                    for issue in issues:
                        me = issue.get('maintenance_entity')
                        if me and isinstance(me, dict) and me.get('id'):
                            me_id = me['id']
                            if me_id not in maintenance_entities:
                                maintenance_entities[me_id] = {
                                    'id': me_id,
                                    'name': me.get('name', 'Без названия'),
                                    'company_id': company_id,
                                    'source': 'issues'
                                }
                                logger.info(f"  ✓ Найден через заявку: {me.get('name', 'Без названия')} (ID: {me_id})")
                    
                    if maintenance_entities:
                        result = list(maintenance_entities.values())
                        logger.info(f"✅ Через заявки: найдено {len(result)} уникальных объектов")
                        return result
                    else:
                        logger.info(f"❌ Через заявки: нет объектов для компании {company_id}")
                else:
                    logger.warning(f"⚠️ Поиск через заявки: неожиданный формат ответа")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка в поиске через заявки: {e}")
            
            # Если ничего не найдено
            logger.warning(f"⚠️ Все методы исчерпаны: нет объектов обслуживания для компании {company_id}")
            return []
            
        except Exception as e:
            logger.error(f"❌ Общая ошибка поиска объектов обслуживания: {e}")
            return []
