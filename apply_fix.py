#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import asyncio
import logging
from pprint import pprint
import config
from services.okdesk_api import OkdeskAPI

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


async def fix_okdesk_api():
    """Функция для применения исправления и проверки его работы"""
    
    # Создаем экземпляр API клиента
    api = OkdeskAPI()
    
    # Идентификатор заявки для теста (используйте существующий ID)
    issue_id = 112  # Измените на ID вашей тестовой заявки
    
    # Телефон пользователя для поиска
    test_phone = "+79133446565"  # Телефон из вашего теста
    
    # Текст комментария
    comment_text = "Тестовый комментарий для проверки исправления"
    
    # Сначала найдем контакт по телефону
    contact = await api.find_contact_by_phone(test_phone)
    
    if contact and 'id' in contact:
        logger.info(f"✅ Найден контакт: {contact.get('name', 'Без имени')} (ID: {contact.get('id')})")
        
        # Создаем комментарий, используя новый параметр client_phone
        response = await api.add_comment(
            issue_id=issue_id,
            content=comment_text,
            client_phone=test_phone
        )
        
        if response and 'id' in response:
            logger.info(f"✅ Комментарий успешно создан с ID: {response['id']}")
            return True
        else:
            logger.error(f"❌ Ошибка при создании комментария: {response}")
            return False
    else:
        logger.error(f"❌ Контакт с телефоном {test_phone} не найден")
        return False


async def main():
    """Основная функция для запуска теста исправления"""
    logger.info("🚀 Запуск проверки исправления для добавления комментариев")
    
    # Проверяем и применяем исправление
    success = await fix_okdesk_api()
    
    if success:
        logger.info("✅ Исправление успешно применено и проверено")
        
        # Рекомендации по развертыванию
        logger.info("\n📋 Инструкции по развертыванию исправления:")
        logger.info("1. Загрузите изменения на сервер:")
        logger.info("   git pull origin master")
        logger.info("2. Перезапустите контейнеры:")
        logger.info("   docker-compose down && docker-compose up -d --build")
        logger.info("3. Проверьте логи после развертывания:")
        logger.info("   docker-compose logs -f")
    else:
        logger.error("❌ Исправление не работает, требуется дополнительная отладка")


if __name__ == "__main__":
    asyncio.run(main())
