import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Telegram Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Okdesk API Configuration
OKDESK_API_URL = os.getenv("OKDESK_API_URL")
OKDESK_API_TOKEN = os.getenv("OKDESK_API_TOKEN")
OKDESK_PORTAL_URL = os.getenv("OKDESK_PORTAL_URL", "https://yapomogu55.okdesk.ru")
OKDESK_PORTAL_TOKEN = os.getenv("OKDESK_PORTAL_TOKEN")
OKDESK_SYSTEM_USER_ID_STR = os.getenv("OKDESK_SYSTEM_USER_ID", "5")
OKDESK_SYSTEM_USER_ID = int(OKDESK_SYSTEM_USER_ID_STR) if OKDESK_SYSTEM_USER_ID_STR and OKDESK_SYSTEM_USER_ID_STR.isdigit() else None

# Webhook Configuration
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/okdesk-webhook")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

# Database Configuration
# PostgreSQL Configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "okdesk_bot")
POSTGRES_USER = os.getenv("POSTGRES_USER", "okdesk_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "changeme123")

# Default PostgreSQL URL
DEFAULT_POSTGRES_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Fallback to SQLite for local development
if os.path.exists("/app/data"):
    # Docker with SQLite fallback
    DEFAULT_DB_PATH = "sqlite:////app/data/okdesk_bot.db"
else:
    # Local SQLite
    DEFAULT_DB_PATH = "sqlite:///data/okdesk_bot.db"

# Use PostgreSQL if POSTGRES_HOST is set and not 'sqlite', otherwise use SQLite
if POSTGRES_HOST and POSTGRES_HOST.lower() != 'sqlite':
    DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_POSTGRES_URL)
else:
    DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_PATH)

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
