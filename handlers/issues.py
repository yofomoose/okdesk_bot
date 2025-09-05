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
    print(f"🔘 Обработка callback: {callback.data}")
    identifier = int(callback.data.split("_")[-1])
    print(f"🔢 Извлечен идентификатор: {identifier}")
    
    # Пытаемся найти заявку по ID или номеру
    issue = IssueService.get_issue_by_id(identifier)
    if not issue:
        print(f"🔍 Не найдено по ID {identifier}, ищу по номеру...")
        issue = IssueService.get_issue_by_number(identifier)
    
    if not issue:
        print(f"❌ Заявка с идентификатором {identifier} не найдена")
        await callback.message.edit_text("❌ Заявка не найдена")
        return
    
    print(f"✅ Заявка найдена: #{issue.issue_number} (ID: {issue.id})")
    await state.update_data(issue_id=issue.id)
    
    await callback.message.edit_text(
        f"💬 Добавление комментария к заявке #{issue.issue_number}\n"
        f"📝 {issue.title}\n\n"
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
            logger.info(f"🔍 Пользователь {user.telegram_id} добавляет комментарий к заявке {issue.okdesk_issue_id}")
            logger.info(f"📋 okdesk_contact_id: {user.okdesk_contact_id}")
            
            # Если у пользователя есть contact_id, создаем комментарий от его имени
            contact_id = user.okdesk_contact_id
            if not contact_id:
                # Пытаемся найти контакт по номеру телефона через Okdesk API
                logger.info(f"🔍 Ищем контакт по номеру телефона: {user.phone}")
                found_contact = await okdesk_api.find_contact_by_phone(user.phone)
                if found_contact and 'id' in found_contact:
                    contact_id = found_contact['id']
                    logger.info(f"✅ Найден существующий контакт с ID: {contact_id}")
                    # Сохраняем ID контакта в базе данных
                    UserService.update_user_contact_info(
                        user_id=user.id,
                        contact_id=contact_id,
                        auth_code=found_contact.get('authentication_code')
                    )
                else:
                    # Если контакт не найден, создаем новый
                    logger.info(f"� Контакт не найден, создаем новый...")
                    name_parts = user.full_name.split(' ', 1) if user.full_name else ['Клиент', '']
                    first_name = name_parts[0]
                    last_name = name_parts[1] if len(name_parts) > 1 else "Клиент"
                    contact_response = await okdesk_api.create_contact(
                        first_name=first_name,
                        last_name=last_name,
                        phone=user.phone,
                        comment=f"Создан автоматически при добавлении комментария (Telegram ID: {user.telegram_id})"
                    )
                    if contact_response and 'id' in contact_response:
                        contact_id = contact_response['id']
                        logger.info(f"✅ Контакт создан с ID: {contact_id}")
                        UserService.update_user_contact_info(
                            user_id=user.id,
                            contact_id=contact_id,
                            auth_code=contact_response.get('authentication_code')
                        )
                    else:
                        logger.error(f"❌ Не удалось создать контакт для пользователя {user.telegram_id}")
                        logger.error(f"Ответ API: {contact_response}")
                        await message.answer("❌ Не удалось создать контакт для комментария. Попробуйте позже или обратитесь к администратору.")
                        await state.clear()
                        return
            # Создаем комментарий от имени найденного или нового контакта
            response = await okdesk_api.add_comment(
                issue_id=issue.okdesk_issue_id,
                content=f"{comment_text}\n\n(Отправлено через Telegram бот)",
                author_id=contact_id,
                author_type="contact"
            )
            comment_source = "от вашего имени"
            
            if response and response.get("id"):
                logger.info(f"✅ Комментарий успешно добавлен к заявке #{issue.issue_number}")
                logger.info(f"📝 ID комментария: {response.get('id')}")
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
                logger.error(f"❌ Ошибка при добавлении комментария к заявке #{issue.issue_number}")
                logger.error(f"Ответ API: {response}")
                error_msg = f"❌ Ошибка при добавлении комментария к заявке #{issue.issue_number}"
                if isinstance(response, dict):
                    error_details = response.get("error") or response.get("errors")
                    if error_details:
                        error_msg += f"\n🔍 Детали: {error_details}"
                        logger.error(f"Детали ошибки: {error_details}")
                    if "author" in str(response).lower():
                        error_msg += f"\n👤 Проблема с автором (ID: {user.okdesk_contact_id})"
                        logger.error(f"Проблема с автором комментария")
                
                await message.answer(error_msg)
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
    user = UserService.get_user_by_telegram_id(callback.from_user.id)
    
    # Если не удалось получить пользователя из базы, показываем меню с регистрацией
    if not user or not is_user_registered(user):
        await callback.message.edit_text(
            "❌ Вы не зарегистрированы в системе.\n"
            "Используйте команду /start для регистрации."
        )
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Создать заявку", callback_data="create_issue")],
        [InlineKeyboardButton(text="📋 Мои заявки", callback_data="my_issues")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")]
    ])
    
    await callback.message.edit_text(
        "🏠 Главное меню\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("add_comment_"))
async def start_add_comment(callback: CallbackQuery, state: FSMContext):
    """Начать добавление комментария к заявке"""
    issue_number = callback.data.split("_")[-1]
    
    # Находим заявку по номеру
    issue = IssueService.get_issue_by_number(int(issue_number))
    if not issue:
        await callback.answer("❌ Заявка не найдена")
        return
    
    # Проверяем, что пользователь является автором заявки
    if issue.telegram_user_id != callback.from_user.id:
        await callback.answer("❌ Вы не можете комментировать чужую заявку")
        return
    
    await callback.message.edit_text(
        f"💬 Добавление комментария к заявке #{issue.issue_number}\n\n"
        f"📝 {issue.title}\n\n"
        f"Напишите ваш комментарий:"
    )
    
    # Сохраняем ID заявки в состоянии
    await state.update_data(issue_id=issue.id)
    await state.set_state(IssueStates.waiting_for_comment)
    await callback.answer()
