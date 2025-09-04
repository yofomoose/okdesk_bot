#!/usr/bin/env python3
"""
Проверка готовности Docker контейнеров
"""
import subprocess
import sys
import os

def check_docker():
    """Проверяем наличие Docker"""
    try:
        result = subprocess.run(['docker', '--version'], 
                              capture_output=True, text=True, check=True)
        print(f"✅ Docker установлен: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Docker не установлен или недоступен")
        return False

def check_docker_compose():
    """Проверяем наличие Docker Compose"""
    try:
        result = subprocess.run(['docker', 'compose', 'version'], 
                              capture_output=True, text=True, check=True)
        print(f"✅ Docker Compose установлен: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Docker Compose не установлен или недоступен")
        return False

def check_env_file():
    """Проверяем наличие .env файла"""
    if os.path.exists('.env'):
        print("✅ Файл .env найден")
        return True
    else:
        print("❌ Файл .env не найден")
        print("💡 Создайте .env файл на основе .env.example")
        return False

def check_data_directory():
    """Проверяем наличие директории data"""
    if not os.path.exists('data'):
        os.makedirs('data')
        print("✅ Создана директория data/")
    else:
        print("✅ Директория data/ существует")
    return True

def main():
    print("🔍 ПРОВЕРКА ГОТОВНОСТИ DOCKER КОНТЕЙНЕРОВ")
    print("=" * 50)
    
    checks = [
        ("Docker", check_docker),
        ("Docker Compose", check_docker_compose),
        (".env файл", check_env_file),
        ("Директория data", check_data_directory)
    ]
    
    all_passed = True
    
    for name, check_func in checks:
        print(f"\n📋 Проверка: {name}")
        if not check_func():
            all_passed = False
    
    print(f"\n{'='*50}")
    
    if all_passed:
        print("🚀 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
        print("\n📝 Следующие шаги:")
        print("1. Отредактируйте .env файл с вашими токенами")
        print("2. Запустите: docker-compose up -d")
        print("3. Проверьте логи: docker-compose logs -f")
    else:
        print("❌ НЕКОТОРЫЕ ПРОВЕРКИ НЕ ПРОЙДЕНЫ")
        print("\n💡 Исправьте ошибки и запустите проверку снова")
        sys.exit(1)

if __name__ == "__main__":
    main()
