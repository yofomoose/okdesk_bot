#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт быстрого развертывания обновлений с медиафайлами
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Выполнить команду с выводом"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(f"✅ {description} - успешно")
            if result.stdout.strip():
                print(f"   {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} - ошибка")
            if result.stderr.strip():
                print(f"   {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - превышен тайм-аут")
        return False
    except Exception as e:
        print(f"💥 {description} - исключение: {e}")
        return False

def check_docker():
    """Проверить доступность Docker"""
    return run_command("docker --version", "Проверка Docker")

def main():
    """Основная функция развертывания"""
    print("🚀 РАЗВЕРТЫВАНИЕ ОБНОВЛЕНИЙ МЕДИАФАЙЛОВ")
    print("=" * 50)
    
    # Проверяем Docker
    if not check_docker():
        print("❌ Docker недоступен. Установите Docker и попробуйте снова.")
        sys.exit(1)
    
    # Список команд для развертывания
    deployment_steps = [
        ("docker-compose down", "Остановка контейнеров"),
        ("docker-compose build --no-cache okdesk_bot", "Пересборка бота"),
        ("docker-compose up -d", "Запуск обновленных контейнеров"),
        ("docker-compose ps", "Проверка статуса контейнеров"),
    ]
    
    success_count = 0
    
    for command, description in deployment_steps:
        if run_command(command, description):
            success_count += 1
        else:
            print(f"\n❌ Развертывание остановлено на этапе: {description}")
            print("🔧 Исправьте ошибку и попробуйте снова")
            sys.exit(1)
        print()  # Пустая строка для читаемости
    
    # Дополнительные проверки
    print("🔍 ДОПОЛНИТЕЛЬНЫЕ ПРОВЕРКИ")
    print("-" * 30)
    
    additional_checks = [
        ("docker-compose logs okdesk_bot | tail -10", "Последние логи бота"),
        ("docker-compose logs okdesk_webhook | tail -5", "Логи webhook"),
    ]
    
    for command, description in additional_checks:
        run_command(command, description)
        print()
    
    # Итоговый отчет
    print("=" * 50)
    print("📊 ИТОГИ РАЗВЕРТЫВАНИЯ")
    print("=" * 50)
    
    if success_count == len(deployment_steps):
        print("🎉 ВСЕ ЭТАПЫ РАЗВЕРТЫВАНИЯ ЗАВЕРШЕНЫ УСПЕШНО!")
        print("\n📋 Новые функции активированы:")
        print("   ✅ Поддержка медиафайлов в комментариях")
        print("   ✅ Улучшенный вывод сообщений") 
        print("   ✅ Оптимизированная оценка заявок")
        print("\n🧪 Для тестирования запустите:")
        print("   python test_media_comments.py")
        print("\n📱 Протестируйте в Telegram боте:")
        print("   1. Создайте заявку")
        print("   2. Добавьте комментарий с фото")
        print("   3. Проверьте оценку заявки")
    else:
        print("⚠️ РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО С ОШИБКАМИ")
        print(f"   Успешно: {success_count}/{len(deployment_steps)} этапов")
        print("   Проверьте логи и исправьте ошибки")
    
    print("=" * 50)

if __name__ == "__main__":
    # Проверяем, что мы в правильной директории
    if not os.path.exists("docker-compose.yml"):
        print("❌ Файл docker-compose.yml не найден")
        print("   Запустите скрипт из корневой директории проекта")
        sys.exit(1)
    
    main()