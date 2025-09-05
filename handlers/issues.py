from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.crud import UserService, IssueService, CommentService
from services.okdesk_api import OkdeskAPI
from models.database import SessionLocal, Issue
from utils.helpers import create_issue_title
import config
import logging

logger = logging.getLogger(__name__)
router = Router()

def is_user_registered(user) -> bool:
    """Проверяет, зарегистрирован ли пользователь по фактическим данным"""
    if not user:
        return False
    
    if user.user_type == "physical" and user.full_name and user.phone:
        return True
    elif user.user_type == "legal" and user.inn_company:
        return True
    
    return False

class IssueStates(StatesGroup):
    waiting_for_description = State()
    waiting_for_comment = State()

@router.message(Command("menu"))
async def cmd_menu(message: Message):
    """Главное меню"""
    user = UserService.get_user_by_telegram_id(message.from_user.id)
    
    if not is_user_registered(user):
        await message.answer(
            "❌ Вы не зарегистрированы в системе.\n"
            "Используйте команду /start для регистрации."
        )
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Создать заявку", callback_data="create_issue")],
        [InlineKeyboardButton(text="📋 Мои заявки", callback_data="my_issues")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")]
    ])
    
    await message.answer(
        "🏠 Главное меню\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Справка по командам бота"""
    help_text = """
🤖 **Справка по боту**

**Основные команды:**
/start - Регистрация в системе
/menu - Главное меню
/issue - Быстрое создание заявки
/help - Эта справка

**Как создать заявку:**
1. Напишите /issue
2. Опишите проблему одним сообщением
3. Получите номер заявки и ссылку

**Примеры заявок:**
• "Не работает принтер в кабинете 205"
• "Нужно настроить доступ к сети"
• "Сломался монитор, экран мигает"

**Поддержка:** Все ваши заявки автоматически попадают в систему поддержки и будут обработаны специалистами.
"""
    
    await message.answer(help_text)

@router.message(Command("issue"))
async def cmd_create_issue(message: Message, state: FSMContext):
    """Быстрое создание заявки через команду"""
    user = UserService.get_user_by_telegram_id(message.from_user.id)
    
    if not is_user_registered(user):
        await message.answer(
            "❌ Вы не зарегистрированы в системе.\n"
            "Используйте команду /start для регистрации."
        )
        return
    
    await message.answer(
        "📝 Быстрое создание заявки\n\n"
        "Опишите вашу проблему или запрос одним сообщением:\n"
        "Например: 'Не работает принтер HP LaserJet в офисе, горит красная лампочка'"
    )
    await state.set_state(IssueStates.waiting_for_description)

@router.callback_query(F.data == "create_issue")
async def create_issue_start(callback: CallbackQuery, state: FSMContext):
    """Начало создания заявки"""
    await callback.message.edit_text(
        "📝 Создание новой заявки\n\n"
        "Опишите вашу проблему или запрос одним сообщением:\n"
        "Например: 'Не работает принтер HP LaserJet в офисе, горит красная лампочка'"
    )
    await state.set_state(IssueStates.waiting_for_description)

@router.message(StateFilter(IssueStates.waiting_for_description))
async def process_issue_description(message: Message, state: FSMContext):
    """Обработка описания заявки"""
    description = message.text.strip()
    
    # Автоматически создаем краткий заголовок из описания
    title = create_issue_title(description)
    
    user = UserService.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден.")
        await state.clear()
        return
        await state.clear()
        return
    
    await message.answer("⏳ Создаю заявку в системе...")
    
    # Подготавливаем данные пользователя для API
    user_data = {
        "user_type": user.user_type,
        "full_name": user.full_name,
        "phone": user.phone,
        "inn_company": user.inn_company,
        "company_id": user.company_id
    }
    
    # Если у пользователя есть контакт в Okdesk, привязываем его к заявке
    if user.okdesk_contact_id:
        user_data["contact_id"] = user.okdesk_contact_id
        logger.info(f"Привязываем контакт к заявке: contact_id = {user.okdesk_contact_id}")
    
    # Создаем заявку через API Okdesk
    okdesk_api = OkdeskAPI()
    try:
        response = await okdesk_api.create_issue(title, description, **user_data)
        
        if response and "id" in response:
            # Заявка успешно создана в Okdesk
            okdesk_issue_id = response["id"]
            issue_number = response.get("number", str(okdesk_issue_id))
            okdesk_url = f"{config.OKDESK_API_URL.replace('/api/v1', '')}/issues/{okdesk_issue_id}"
            
            # Сохраняем заявку в нашей БД
            issue = IssueService.create_issue(
                telegram_user_id=user.telegram_id,
                okdesk_issue_id=okdesk_issue_id,
                title=title,
                description=description,
                status="opened",
                okdesk_url=okdesk_url,
                issue_number=issue_number
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔗 Открыть заявку", url=okdesk_url)],
                [InlineKeyboardButton(text="💬 Добавить комментарий", callback_data=f"add_comment_{issue.id}")],
                [InlineKeyboardButton(text="🔄 Проверить статус", callback_data=f"check_status_{issue.id}")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
            
            await message.answer(
                f"✅ Заявка успешно создана!\n\n"
                f"📋 Номер заявки: #{issue_number}\n"
                f"📝 Заголовок: {title}\n"
                f"📊 Статус: {config.ISSUE_STATUS_MESSAGES.get('opened', 'Открыта')}\n\n"
                f"🔗 Ссылка на заявку: {okdesk_url}\n\n"
                f"Вы можете отслеживать статус заявки и добавлять комментарии.",
                reply_markup=keyboard
            )
        else:
            await message.answer(
                "❌ Ошибка при создании заявки.\n"
                "Попробуйте еще раз или обратитесь к администратору."
            )
    finally:
        await okdesk_api.close()
    
    await state.clear()

@router.callback_query(F.data == "my_issues")
async def show_my_issues(callback: CallbackQuery):
    """Показать заявки пользователя"""
    user = UserService.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    issues = IssueService.get_user_issues(user.telegram_id)
    
    if not issues:
        await callback.message.edit_text(
            "📋 У вас пока нет заявок.\n\n"
            "Создайте первую заявку, используя кнопку ниже:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 Создать заявку", callback_data="create_issue")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
        )
        return
    
    keyboard_buttons = []
    text = "📋 Ваши заявки:\n\n"
    
    for issue in issues[-10:]:  # Показываем последние 10 заявок
        status_emoji = config.ISSUE_STATUS_MESSAGES.get(issue.status, issue.status)
        text += f"#{issue.issue_number} - {issue.title}\n{status_emoji}\n\n"
        
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"#{issue.issue_number} - {issue.title[:20]}...",
                callback_data=f"view_issue_{issue.id}"
            )
        ])
    
    keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("view_issue_"))
async def view_issue(callback: CallbackQuery):
    """Просмотр конкретной заявки"""
    issue_id = int(callback.data.split("_")[-1])
    
    # Получаем заявку из БД
    db = SessionLocal()
    try:
        issue = db.query(Issue).filter(Issue.id == issue_id).first()
        if not issue:
            await callback.answer("❌ Заявка не найдена")
            return
        
        # Получаем актуальную информацию из Okdesk
        okdesk_api = OkdeskAPI()
        try:
            okdesk_issue = await okdesk_api.get_issue(issue.okdesk_issue_id)
            
            if okdesk_issue:
                # Обновляем статус в нашей БД
                current_status = okdesk_issue.get("status", issue.status)
                # Если статус - словарь, извлекаем код
                if isinstance(current_status, dict):
                    current_status = current_status.get("code", current_status)
                
                if current_status != issue.status:
                    issue.status = current_status
                    db.commit()
        finally:
            await okdesk_api.close()
        
        status_text = config.ISSUE_STATUS_MESSAGES.get(issue.status, issue.status)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Открыть заявку", url=issue.okdesk_url)],
            [InlineKeyboardButton(text="💬 Добавить комментарий", callback_data=f"add_comment_{issue.id}")],
            [InlineKeyboardButton(text="🔄 Обновить статус", callback_data=f"check_status_{issue.id}")],
            [InlineKeyboardButton(text="📋 Все заявки", callback_data="my_issues")]
        ])
        
        await callback.message.edit_text(
            f"📋 Заявка #{issue.issue_number}\n\n"
            f"📝 Заголовок: {issue.title}\n"
            f"📄 Описание: {issue.description or 'Не указано'}\n"
            f"📊 Статус: {status_text}\n"
            f"📅 Создана: {issue.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"🔗 Ссылка: {issue.okdesk_url}",
            reply_markup=keyboard
        )
    finally:
        db.close()

@router.callback_query(F.data.startswith("add_comment_"))
async def add_comment_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления комментария"""
    issue_id = int(callback.data.split("_")[-1])
    await state.update_data(issue_id=issue_id)
    
    await callback.message.edit_text(
        "💬 Добавление комментария\n\n"
        "Введите текст комментария:"
    )
    await state.set_state(IssueStates.waiting_for_comment)

@router.message(StateFilter(IssueStates.waiting_for_comment))
async def process_comment(message: Message, state: FSMContext):
    """Обработка комментария"""
    data = await state.get_data()
    issue_id = data["issue_id"]
    comment_text = message.text
    
    # Получаем заявку
    db = SessionLocal()
    try:
        issue = db.query(Issue).filter(Issue.id == issue_id).first()
        if not issue:
            await message.answer("❌ Заявка не найдена")
            await state.clear()
            return
        
        await message.answer("⏳ Добавляю комментарий...")
        
        # Получаем информацию о пользователе
        user = UserService.get_user_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("❌ Ошибка: пользователь не найден")
            await state.clear()
            return
        
        # Добавляем комментарий через API Okdesk
        okdesk_api = OkdeskAPI()
        try:
            # Если у пользователя есть contact_id, создаем комментарий от его имени
            if user.okdesk_contact_id:
                response = await okdesk_api.add_comment(
                    issue_id=issue.okdesk_issue_id,
                    content=f"{comment_text}\n\n(Отправлено через Telegram бот)",
                    author_id=user.okdesk_contact_id,
                    author_type="contact"
                )
                comment_source = "от вашего имени"
            else:
                # Для пользователей без contact_id используем системного пользователя с указанием имени клиента
                formatted_comment = f"💬 **{user.full_name}** (через Telegram):\n\n{comment_text}"
                
                response = await okdesk_api.add_comment(
                    issue_id=issue.okdesk_issue_id,
                    content=formatted_comment,
                    author_id=config.OKDESK_SYSTEM_USER_ID
                )
                comment_source = "через системного пользователя"
            
            if response:
                # Сохраняем комментарий в нашей БД
                CommentService.add_comment(
                    issue_id=issue_id,
                    telegram_user_id=message.from_user.id,
                    content=comment_text,
                    okdesk_comment_id=response.get("id")
                )
                
                await message.answer(
                    f"✅ Комментарий добавлен к заявке #{issue.issue_number}\n\n"
                    f"💬 Ваш комментарий: {comment_text}\n"
                    f"👤 Создан: {comment_source}\n\n"
                    f"📝 Также вы можете комментировать напрямую через веб-портал:\n"
                    f"🌐 https://yapomogu55.okdesk.ru"
                )
            else:
                await message.answer("❌ Ошибка при добавлении комментария")
        finally:
            await okdesk_api.close()
    finally:
        db.close()
    
    await state.clear()

@router.callback_query(F.data.startswith("check_status_"))
async def check_status(callback: CallbackQuery):
    """Проверка статуса заявки"""
    issue_id = int(callback.data.split("_")[-1])
    
    db = SessionLocal()
    try:
        issue = db.query(Issue).filter(Issue.id == issue_id).first()
        if not issue:
            await callback.answer("❌ Заявка не найдена")
            return
        
        # Получаем актуальную информацию из Okdesk
        okdesk_api = OkdeskAPI()
        try:
            okdesk_issue = await okdesk_api.get_issue(issue.okdesk_issue_id)
            
            if okdesk_issue:
                old_status = issue.status
                new_status = okdesk_issue.get("status", issue.status)
                # Если статус - словарь, извлекаем код
                if isinstance(new_status, dict):
                    new_status = new_status.get("code", new_status)
                
                if new_status != old_status:
                    # Статус изменился
                    issue.status = new_status
                    db.commit()
                    
                    status_text = config.ISSUE_STATUS_MESSAGES.get(new_status, new_status)
                    await callback.answer(f"📊 Статус обновлен: {status_text}")
                else:
                    status_text = config.ISSUE_STATUS_MESSAGES.get(new_status, new_status)
                    await callback.answer(f"📊 Текущий статус: {status_text}")
            else:
                await callback.answer("❌ Не удалось получить актуальную информацию")
        finally:
            await okdesk_api.close()
    finally:
        db.close()

@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    """Показать профиль пользователя"""
    user = UserService.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    if user.user_type == "physical":
        profile_text = (
            f"👤 Ваш профиль\n\n"
            f"Тип: Физическое лицо\n"
            f"ФИО: {user.full_name}\n"
            f"Телефон: {user.phone}\n"
            f"Дата регистрации: {user.created_at.strftime('%d.%m.%Y')}"
        )
    elif user.user_type == "legal":
        profile_text = (
            f"🏢 Ваш профиль\n\n"
            f"Тип: Юридическое лицо\n"
            f"ИНН: {user.inn_company}\n"
            f"Компания: {user.company_name or 'Не найдена в системе'}\n"
            f"Дата регистрации: {user.created_at.strftime('%d.%m.%Y')}"
        )
    else:
        profile_text = "❌ Профиль не настроен"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(profile_text, reply_markup=keyboard)

@router.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    await cmd_menu(callback.message)
