import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Telegram Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Okdesk API Configuration
OKDESK_API_URL = os.getenv("OKDESK_API_URL")
OKDESK_API_TOKEN = os.getenv("OKDESK_API_TOKEN")

# Webhook Configuration
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/okdesk-webhook")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////app/data/okdesk_bot.db")

# Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")  # Слушаем на всех интерфейсах
PORT = int(os.getenv("PORT", 8000))

# Okdesk API Endpoints
OKDESK_ENDPOINTS = {
    "companies": "/companies",
    "issues": "/issues",
    "comments": "/issues/{issue_id}/comments",
    "equipments": "/equipments"
}

# User Types
USER_TYPES = {
    "individual": "physical",
    "company": "legal"
}

# Issue Status Messages
ISSUE_STATUS_MESSAGES = {
    "opened": "🟡 Заявка открыта",
    "in_progress": "🔵 Заявка в работе", 
    "on_hold": "⏸️ Заявка приостановлена",
    "resolved": "✅ Заявка решена",
    "closed": "🔒 Заявка закрыта"
}
