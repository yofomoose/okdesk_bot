from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, BigInteger, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import config

# Создаем базовый класс для моделей
Base = declarative_base()

# Создаем движок базы данных (без echo для production)
engine = create_engine(config.DATABASE_URL, echo=False)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    user_type = Column(String, nullable=False)  # "physical" или "legal"
    
    # Для физических лиц
    full_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    contact_auth_code = Column(String, nullable=True)  # Код авторизации контакта в Okdesk
    okdesk_contact_id = Column(Integer, nullable=True)  # ID контакта в Okdesk
    portal_token = Column(String, nullable=True)  # Персональный токен авторизации для портала
    
    # Для юридических лиц
    inn_company = Column(String, nullable=True)
    company_id = Column(Integer, nullable=True)  # ID компании в Okdesk
    company_name = Column(String, nullable=True)
    service_object_name = Column(String, nullable=True)  # Название объекта обслуживания
    
    # Дополнительные поля
    is_registered = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Issue(Base):
    """Модель заявки"""
    __tablename__ = "issues"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_user_id = Column(BigInteger, nullable=False)
    okdesk_issue_id = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False)
    priority = Column(String, nullable=True)
    
    # Ссылки и идентификаторы
    okdesk_url = Column(String, nullable=True)
    issue_number = Column(String, nullable=True)
    telegram_message_id = Column(Integer, nullable=True)  # ID сообщения в Telegram с деталями заявки
    
    # Оценка качества работы (1-5 звезд)
    rating = Column(Integer, nullable=True)
    rating_comment = Column(Text, nullable=True)
    
    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Comment(Base):
    """Модель комментария"""
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, nullable=False)  # ID заявки в нашей БД
    okdesk_comment_id = Column(Integer, nullable=True)  # ID комментария в Okdesk
    telegram_user_id = Column(BigInteger, nullable=False)
    content = Column(Text, nullable=False)
    is_from_okdesk = Column(Boolean, default=False)  # Комментарий пришел из Okdesk
    
    created_at = Column(DateTime, default=datetime.utcnow)

# Создаем все таблицы ТОЛЬКО если их нет
def create_tables():
    """
    Создает таблицы в базе данных, если они не существуют.
    Использует checkfirst=True для безопасного создания.
    """
    try:
        # checkfirst=True означает: создать таблицы только если их нет
        Base.metadata.create_all(bind=engine, checkfirst=True)
        print("📊 Таблицы проверены/созданы в базе данных")
        return True
    except Exception as e:
        print(f"❌ Ошибка при создании таблиц: {e}")
        return False

# Функция для получения сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
