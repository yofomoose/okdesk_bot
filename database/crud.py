from models.database import SessionLocal, User, Issue, Comment
from sqlalchemy.orm import Session
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

class UserService:
    """Сервис для работы с пользователями"""
    
    @staticmethod
    def get_user_by_telegram_id(telegram_id: int) -> Optional[User]:
        """Получить пользователя по Telegram ID"""
        try:
            db = SessionLocal()
            try:
                return db.query(User).filter(User.telegram_id == telegram_id).first()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Ошибка получения пользователя {telegram_id}: {e}")
            return None
    
    @staticmethod
    def create_user(telegram_id: int, username: str = None) -> User:
        """Создать нового пользователя"""
        try:
            db = SessionLocal()
            try:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    user_type="",  # Будет установлен позже
                    is_registered=False
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                return user
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Ошибка создания пользователя {telegram_id}: {e}")
            # Возвращаем фиктивного пользователя для работы без базы данных
            user = User()
            user.telegram_id = telegram_id
            user.username = username
            user.id = -1  # Фиктивный ID
            user.user_type = ""
            user.is_registered = False
            return user
    
    @staticmethod
    def update_user_physical(user_id: int, full_name: str, phone: str) -> Optional[User]:
        """Обновить данные физического лица"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.user_type = "physical"
                user.full_name = full_name
                user.phone = phone
                user.is_registered = True
                db.commit()
                db.refresh(user)
            return user
        finally:
            db.close()
    
    @staticmethod
    def update_user_legal(user_id: int, inn_company: str, company_id: int = None, company_name: str = None) -> Optional[User]:
        """Обновить данные юридического лица"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.user_type = "legal"
                user.inn_company = inn_company
                user.company_id = company_id
                user.company_name = company_name
                user.is_registered = True
                db.commit()
                db.refresh(user)
            return user
        finally:
            db.close()
    
    @staticmethod
    def update_user_auth_code(user_id: int, auth_code: str) -> Optional[User]:
        """Обновить код авторизации пользователя"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.contact_auth_code = auth_code
                db.commit()
                db.refresh(user)
            return user
        finally:
            db.close()
    
    @staticmethod
    def update_user_contact_info(user_id: int, contact_id: int, auth_code: str = None) -> Optional[User]:
        """Обновить информацию о контакте пользователя"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.okdesk_contact_id = contact_id
                if auth_code:
                    user.contact_auth_code = auth_code
                db.commit()
                db.refresh(user)
            return user
        finally:
            db.close()
    
    @staticmethod
    def update_contact_id_by_telegram_id(telegram_id: int, contact_id: int) -> Optional[User]:
        """Обновить ID контакта OkDesk для пользователя по telegram_id"""
        logger.info(f"Обновление contact_id={contact_id} для пользователя telegram_id={telegram_id}")
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                user.okdesk_contact_id = contact_id
                db.commit()
                db.refresh(user)
                logger.info(f"✅ Успешно обновлен контакт для пользователя {telegram_id}: contact_id={contact_id}")
                return user
            else:
                logger.warning(f"⚠️ Пользователь с telegram_id={telegram_id} не найден в базе данных")
                return None
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении contact_id для пользователя {telegram_id}: {e}")
            return None
        finally:
            db.close()
    
    @staticmethod
    def update_company_id_by_telegram_id(telegram_id: int, company_id: int) -> Optional[User]:
        """Обновить ID компании OkDesk для пользователя по telegram_id"""
        logger.info(f"Обновление company_id={company_id} для пользователя telegram_id={telegram_id}")
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                user.okdesk_company_id = company_id
                db.commit()
                db.refresh(user)
                logger.info(f"✅ Успешно обновлена компания для пользователя {telegram_id}: company_id={company_id}")
                return user
            else:
                logger.warning(f"⚠️ Пользователь с telegram_id={telegram_id} не найден в базе данных")
                return None
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении company_id для пользователя {telegram_id}: {e}")
            return None
        finally:
            db.close()

class IssueService:
    """Сервис для работы с заявками"""
    
    @staticmethod
    def create_issue(telegram_user_id: int, okdesk_issue_id: int, title: str, 
                    description: str = None, status: str = "opened", 
                    okdesk_url: str = None, issue_number: str = None) -> Issue:
        """Создать новую заявку"""
        db = SessionLocal()
        try:
            issue = Issue(
                telegram_user_id=telegram_user_id,
                okdesk_issue_id=okdesk_issue_id,
                title=title,
                description=description,
                status=status,
                okdesk_url=okdesk_url,
                issue_number=issue_number
            )
            db.add(issue)
            db.commit()
            db.refresh(issue)
            return issue
        finally:
            db.close()
    
    @staticmethod
    def get_user_issues(telegram_user_id: int) -> List[Issue]:
        """Получить все заявки пользователя"""
        db = SessionLocal()
        try:
            return db.query(Issue).filter(Issue.telegram_user_id == telegram_user_id).all()
        finally:
            db.close()
    
    @staticmethod
    def get_all_issues() -> List[Issue]:
        """Получить все заявки (для отладки)"""
        db = SessionLocal()
        try:
            return db.query(Issue).all()
        finally:
            db.close()
    
    @staticmethod
    def get_issue_by_okdesk_id(okdesk_issue_id: int) -> Optional[Issue]:
        """Получить заявку по ID в Okdesk"""
        db = SessionLocal()
        try:
            return db.query(Issue).filter(Issue.okdesk_issue_id == okdesk_issue_id).first()
        finally:
            db.close()
    
    @staticmethod
    def get_issue_by_id(issue_id: int) -> Optional[Issue]:
        """Получить заявку по ID"""
        db = SessionLocal()
        try:
            return db.query(Issue).filter(Issue.id == issue_id).first()
        finally:
            db.close()
    
    @staticmethod
    def get_issue_by_number(issue_number: int) -> Optional[Issue]:
        """Получить заявку по номеру"""
        db = SessionLocal()
        try:
            return db.query(Issue).filter(Issue.issue_number == str(issue_number)).first()
        finally:
            db.close()
    
    @staticmethod
    def update_issue_status(issue_id: int, status: str) -> Optional[Issue]:
        """Обновить статус заявки"""
        db = SessionLocal()
        try:
            issue = db.query(Issue).filter(Issue.id == issue_id).first()
            if issue:
                issue.status = status
                db.commit()
                db.refresh(issue)
            return issue
        finally:
            db.close()

class CommentService:
    """Сервис для работы с комментариями"""
    
    @staticmethod
    def add_comment(issue_id: int, telegram_user_id: int, content: str, 
                   okdesk_comment_id: int = None, is_from_okdesk: bool = False) -> Comment:
        """Добавить комментарий"""
        db = SessionLocal()
        try:
            comment = Comment(
                issue_id=issue_id,
                telegram_user_id=telegram_user_id,
                content=content,
                okdesk_comment_id=okdesk_comment_id,
                is_from_okdesk=is_from_okdesk
            )
            db.add(comment)
            db.commit()
            db.refresh(comment)
            return comment
        finally:
            db.close()
    
    @staticmethod
    def get_issue_comments(issue_id: int) -> List[Comment]:
        """Получить все комментарии заявки"""
        db = SessionLocal()
        try:
            return db.query(Comment).filter(Comment.issue_id == issue_id).all()
        finally:
            db.close()
