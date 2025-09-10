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


async def verify_deployment():
    """Проверка успешности развертывания исправления"""
    
    # Создаем экземпляр API клиента
    api = OkdeskAPI()
    
    # Проверяем соединение с API
    logger.info("🔍 Проверка соединения с API...")
    
    # Получаем список заявок для проверки соединения
    issues = await api.get_issues(limit=1)
    
    if not issues:
        logger.error("❌ Не удалось получить список заявок. Проверьте подключение к API.")
        return False
    
    logger.info("✅ Соединение с API работает")
    
    # Проверяем поиск контактов по телефону
    logger.info("🔍 Проверка поиска контактов по телефону...")
    test_phone = "+79133446565"  # Используйте существующий номер телефона
    
    contact = await api.find_contact_by_phone(test_phone)
    
    if not contact:
        logger.error(f"❌ Не удалось найти контакт по телефону: {test_phone}")
        logger.error("Проверьте работу метода find_contact_by_phone")
        return False
    
    logger.info(f"✅ Поиск контактов работает. Найден контакт: {contact.get('name', 'Без имени')}")
    
    # Создаем тестовую заявку
    logger.info("🔍 Проверка создания заявки с привязкой клиента...")
    
    title = "Тестовая заявка для проверки развертывания"
    description = "Эта заявка создана автоматически для проверки успешности развертывания исправления"
    
    response = await api.create_issue(
        title=title,
        description=description,
        contact_id=contact['id']
    )
    
    if not response or 'id' not in response:
        logger.error("❌ Не удалось создать тестовую заявку")
        logger.error(f"Ответ API: {response}")
        return False
    
    issue_id = response['id']
    logger.info(f"✅ Тестовая заявка создана с ID: {issue_id}")
    
    # Получаем информацию о созданной заявке для проверки привязки клиента
    issue = await api.get_issue(issue_id)
    
    if not issue:
        logger.error(f"❌ Не удалось получить данные заявки {issue_id}")
        return False
    
    client_info = issue.get('client', {})
    if not client_info:
        logger.warning("⚠️ Клиент не привязан к заявке в ответе API")
    else:
        contact_info = client_info.get('contact', {})
        if contact_info and contact_info.get('id') == contact['id']:
            logger.info("✅ Привязка клиента к заявке работает корректно")
        else:
            logger.warning("⚠️ Привязка клиента к заявке не работает или работает неправильно")
    
    # Добавляем комментарий к созданной заявке
    logger.info("🔍 Проверка добавления комментария...")
    
    comment_text = "Тестовый комментарий для проверки исправления"
    
    # Сначала пробуем с явным указанием author_id и author_type
    comment_response = await api.add_comment(
        issue_id=issue_id,
        content=comment_text,
        author_id=contact['id'],
        author_type="contact"
    )
    
    if comment_response and ('id' in comment_response or 'success' in comment_response):
        logger.info("✅ Создание комментария с явным указанием автора работает")
    else:
        logger.error("❌ Не удалось создать комментарий с явным указанием автора")
        logger.error(f"Ответ API: {comment_response}")
    
    # Затем пробуем только с указанием телефона
    comment_response2 = await api.add_comment(
        issue_id=issue_id,
        content=f"{comment_text} (тест с телефоном)",
        client_phone=test_phone
    )
    
    if comment_response2 and ('id' in comment_response2 or 'success' in comment_response2):
        logger.info("✅ Создание комментария с указанием телефона работает")
        logger.info("✅ ИСПРАВЛЕНИЕ УСПЕШНО РАЗВЕРНУТО И РАБОТАЕТ")
        return True
    else:
        logger.error("❌ Не удалось создать комментарий с указанием телефона")
        logger.error(f"Ответ API: {comment_response2}")
        return False


async def main():
    """Основная функция"""
    logger.info("🚀 Проверка успешности развертывания исправления")
    success = await verify_deployment()
    
    if success:
        logger.info("✅ Исправление успешно развернуто и работает")
    else:
        logger.error("❌ Обнаружены проблемы с исправлением")


if __name__ == "__main__":
    asyncio.run(main())
