# -*- coding: utf-8 -*-

"""
Обновленный метод для поиска компании по ИНН через API OkDesk.

1. Скопируйте весь метод
2. Замените текущий метод find_company_by_inn в файле services/okdesk_api.py
"""

async def find_company_by_inn(self, inn: str, create_if_not_found: bool = False) -> Optional[Dict]:
    """
    Найти компанию по ИНН и сохранить её ID в базе данных для соответствующих пользователей.
    
    Args:
        inn: ИНН компании для поиска
        create_if_not_found: Создавать компанию, если не найдена (по умолчанию False)
    
    Returns:
        Dict: Данные компании или None, если не найдена
    """
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
        
        # Используем API-запрос с правильным параметром для поиска компании по ИНН
        logger.info(f"🔍 Выполняем поиск компании через API по параметру inn_company={clean_inn}...")
        
        # Делаем запрос с использованием параметра inn_company в соответствии с документацией API
        companies = await self._make_request('GET', f"/companies/list?parameter[inn_company]={clean_inn}")
        
        # Переменная для найденной компании
        company = None
        
        # Проверяем результаты поиска
        if isinstance(companies, list) and companies:
            logger.info(f"✅ Найдено {len(companies)} компаний по запросу inn_company={clean_inn}")
            # Берем первую найденную компанию, так как ИНН должен быть уникальным
            company = companies[0]
            logger.info(f"✅ Выбрана компания: {company.get('name', 'Без названия')} (ID: {company.get('id')})")
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
                from services.database import DatabaseManager
                db = DatabaseManager('okdesk_bot.db')
                
                # Получаем пользователей с этим ИНН, у которых не задан okdesk_company_id
                users = db.execute(
                    "SELECT telegram_id FROM users WHERE inn_company = ? AND okdesk_company_id IS NULL", 
                    (clean_inn,)
                ).fetchall()
                
                for user_row in users:
                    user_id = user_row[0]
                    # Обновляем okdesk_company_id для пользователя
                    db.execute(
                        "UPDATE users SET okdesk_company_id = ? WHERE telegram_id = ?",
                        (company['id'], user_id)
                    )
                    logger.info(f"✅ Обновлен okdesk_company_id={company['id']} для пользователя {user_id} в базе данных")
                
                db.commit()
                db.close()
            except Exception as e:
                logger.error(f"❌ Ошибка при обновлении okdesk_company_id в базе данных: {e}")
            
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
