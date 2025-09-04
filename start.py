import asyncio
import subprocess
import threading
import time
import os
import sys

def run_bot():
    """Запуск Telegram бота"""
    print("🤖 Запуск Telegram бота...")
    subprocess.run([sys.executable, "bot.py"])

def run_webhook():
    """Запуск webhook сервера"""
    print("🌐 Запуск webhook сервера...")
    subprocess.run([sys.executable, "webhook_server.py"])

def check_env_file():
    """Проверка наличия файла .env"""
    if not os.path.exists('.env'):
        print("❌ Файл .env не найден!")
        print("📝 Скопируйте .env.example в .env и заполните необходимые параметры:")
        print("   cp .env.example .env")
        print("\n🔧 Необходимо настроить:")
        print("   - BOT_TOKEN (токен Telegram бота)")
        print("   - OKDESK_API_URL (URL API Okdesk)")
        print("   - OKDESK_API_TOKEN (токен API Okdesk)")
        return False
    return True

def main():
    """Главная функция запуска"""
    print("🚀 Запуск Okdesk Telegram Bot")
    print("=" * 40)
    
    # Проверяем файл конфигурации
    if not check_env_file():
        return
    
    try:
        # Создаем потоки для бота и webhook сервера
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        webhook_thread = threading.Thread(target=run_webhook, daemon=True)
        
        # Запускаем потоки
        bot_thread.start()
        time.sleep(2)  # Небольшая задержка между запусками
        webhook_thread.start()
        
        print("✅ Сервисы запущены!")
        print("📱 Telegram бот работает")
        print("🌐 Webhook сервер работает")
        print("\n🛑 Для остановки нажмите Ctrl+C")
        
        # Ожидаем завершения потоков
        bot_thread.join()
        webhook_thread.join()
        
    except KeyboardInterrupt:
        print("\n🛑 Получен сигнал остановки...")
        print("📴 Останавливаем сервисы...")
        print("✅ Остановлено!")
    except Exception as e:
        print(f"❌ Ошибка при запуске: {e}")

if __name__ == "__main__":
    main()
