from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.crud import UserService, IssueService
from services.okdesk_api import OkdeskAPI
from utils.helpers import validate_phone, normalize_phone, validate_inn
import config
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

router = Router()

def truncate_message(text: str, max_length: int = 4000) -> str:
    """Обрезает сообщение до максимальной длины, сохраняя смысл"""
    if len(text) <= max_length:
        return text
    
    # Обрезаем с запасом и добавляем троеточие
    truncated = text[:max_length - 3] + "..."
    return truncated

async def get_available_service_objects(okdesk_api: OkdeskAPI, company_id: int) -> list:
    """
    Получить доступные объекты обслуживания для компании.
    Использует новый API метод get_maintenance_entities_for_company.
    """
    try:
        logger.info(f"🔍 Получение объектов обслуживания для компании ID={company_id}")
        
        # Используем новый метод API для получения объектов обслуживания для компании
        service_objects = await okdesk_api.get_maintenance_entities_for_company(company_id)
        
        if service_objects:
            logger.info(f"📋 Найдено {len(service_objects)} объектов обслуживания для компании")
            return service_objects
        
        logger.warning("❌ Не удалось получить объекты обслуживания")
        return []
        
    except Exception as e:
        logger.error(f"Ошибка получения объектов обслуживания: {e}")
        return []

def is_user_registered(user) -> bool:
    """Проверяет, зарегистрирован ли пользователь по фактическим данным"""
    if not user:
        return False
    
    if user.user_type == "physical" and user.full_name and user.phone:
        return True
    elif user.user_type == "legal" and user.inn_company:
        return True
    
    return False

class RegistrationStates(StatesGroup):
    waiting_for_user_type = State()
    waiting_for_full_name = State()
    waiting_for_phone = State()
    waiting_for_inn = State()
    waiting_for_branch = State()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    user = UserService.get_user_by_telegram_id(message.from_user.id)
    
    if is_user_registered(user):
        await message.answer(
            f"👋 Добро пожаловать обратно!\n\n"
            f"Вы зарегистрированы как: {get_user_type_text(user.user_type)}\n"
            f"Используйте /menu для доступа к функциям бота."
        )
    else:
        if not user:
            # Создаем нового пользователя
            UserService.create_user(
                telegram_id=message.from_user.id,
                username=message.from_user.username
            )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👤 Физическое лицо", callback_data="register_physical")],
            [InlineKeyboardButton(text="🏢 Юридическое лицо", callback_data="register_legal")]
        ])
        
        await message.answer(
            "🔐 Добро пожаловать в систему подачи заявок!\n\n"
            "Для начала работы необходимо зарегистрироваться.\n"
            "Выберите тип регистрации:",
            reply_markup=keyboard
        )
        await state.set_state(RegistrationStates.waiting_for_user_type)

@router.callback_query(F.data == "register_physical", StateFilter(RegistrationStates.waiting_for_user_type))
async def register_physical(callback: CallbackQuery, state: FSMContext):
    """Регистрация физического лица"""
    await state.update_data(user_type="physical")
    await callback.message.edit_text(
        "👤 Регистрация физического лица\n\n"
        "Введите ваше полное имя (ФИО):"
    )
    await state.set_state(RegistrationStates.waiting_for_full_name)

@router.callback_query(F.data == "register_legal", StateFilter(RegistrationStates.waiting_for_user_type))
async def register_legal(callback: CallbackQuery, state: FSMContext):
    """Регистрация юридического лица"""
    await state.update_data(user_type="legal")
    await callback.message.edit_text(
        "🏢 Регистрация юридического лица\n\n"
        "Введите ваше ФИО (представителя компании):"
    )
    await state.set_state(RegistrationStates.waiting_for_full_name)

@router.message(StateFilter(RegistrationStates.waiting_for_full_name))
async def process_full_name(message: Message, state: FSMContext):
    """Обработка ввода ФИО"""
    await state.update_data(full_name=message.text)
    await message.answer(
        "📱 Введите ваш номер телефона:\n"
        "(в формате +7XXXXXXXXXX или 8XXXXXXXXXX)"
    )
    await state.set_state(RegistrationStates.waiting_for_phone)

@router.message(StateFilter(RegistrationStates.waiting_for_phone))
async def process_phone(message: Message, state: FSMContext):
    """Обработка ввода телефона"""
    phone = message.text.strip()
    
    # Валидация телефона
    if not validate_phone(phone):
        await message.answer(
            "❌ Неверный формат телефона.\n"
            "Введите номер в формате +7XXXXXXXXXX или 8XXXXXXXXXX"
        )
        return
    
    # Нормализуем телефон
    normalized_phone = normalize_phone(phone)
    
    # Получаем данные из состояния
    data = await state.get_data()
    user_type = data.get("user_type")
    
    # Сохраняем телефон в состоянии
    await state.update_data(phone=normalized_phone)
    
    if user_type == "physical":
        # Для физических лиц завершаем регистрацию
        user = UserService.get_user_by_telegram_id(message.from_user.id)
        
        if user:
            # Обновляем данные пользователя
            updated_user = UserService.update_user_physical(
                user_id=user.id,
                full_name=data["full_name"],
                phone=normalized_phone
            )
            
            if updated_user:
                # Создаем контакт в Okdesk с доступом к порталу
                try:
                    okdesk_api = OkdeskAPI()
                    # Правильно разбираем ФИО: Фамилия Имя Отчество
                    name_parts = updated_user.full_name.split(' ')
                    if len(name_parts) >= 2:
                        last_name = name_parts[0]  # Фамилия
                        first_name = name_parts[1]  # Имя
                        patronymic = name_parts[2] if len(name_parts) > 2 else ""  # Отчество
                    else:
                        first_name = updated_user.full_name
                        last_name = "Клиент"
                        patronymic = ""
                    
                    # Используем новую функцию с доступом к порталу
                    contact_response = await okdesk_api.create_contact_with_portal_access(
                        first_name=first_name,
                        last_name=last_name,
                        patronymic=patronymic,
                        phone=updated_user.phone,
                        telegram_username=message.from_user.username,
                        comment=f"Создан автоматически из Telegram бота (ID: {message.from_user.id})",
                        # Параметры доступа к порталу
                        access_level=[
                            'company_issues',  # Отображать заявки компании
                            'allow_close_company_issues'  # Разрешить закрывать заявки компании
                        ]
                    )
                    await okdesk_api.close()
                    
                    if contact_response and 'id' in contact_response:
                        # Сохраняем ID контакта и информацию о доступе к порталу
                        contact_id = contact_response['id']
                        auth_code = contact_response.get('authentication_code')
                        portal_login = contact_response.get('portal_login')
                        portal_password = contact_response.get('portal_password')
                        
                        UserService.update_user_contact_info(
                            user_id=updated_user.id,
                            contact_id=contact_id,
                            auth_code=auth_code
                        )
                        
                        # Формируем информационное сообщение
                        contact_info = f"\n🔗 Контакт создан в Okdesk (ID: {contact_id})"
                        
                        if auth_code:
                            contact_info += f"\n🔐 Код авторизации: {auth_code}"
                        
                        if portal_login and portal_password:
                            if portal_password == "USE_EXISTING_PASSWORD":
                                contact_info += f"\n🔗 У вас уже есть доступ к порталу"
                                contact_info += f"\n🌐 Клиентский портал: {config.OKDESK_PORTAL_URL}"
                            else:
                                contact_info += f"\n👤 Логин портала: {portal_login}"
                                contact_info += f"\n🔑 Пароль портала: {portal_password}"
                                contact_info += f"\n🌐 Вы можете войти в клиентский портал: {config.OKDESK_PORTAL_URL}"
                        else:
                            contact_info += "\n⚠️ Данные для входа в портал будут высланы отдельно"
                    elif contact_response and contact_response.get('error') == 422:
                        # Контакт уже существует
                        contact_info = "\n⚠️ Контакт с таким Telegram username уже существует в Okdesk"
                        contact_info += "\n🔗 Используйте существующий доступ к порталу"
                        contact_info += f"\n🌐 Клиентский портал: {config.OKDESK_PORTAL_URL}"
                    else:
                        contact_info = "\n⚠️ Контакт не удалось создать"
                        
                except Exception as e:
                    logger.error(f"Ошибка создания контакта в Okdesk: {e}")
                    contact_info = "\n⚠️ Ошибка создания контакта"
                
                # Создаем клавиатуру с кнопками быстрого доступа
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📝 Создать заявку", callback_data="create_issue")],
                    [InlineKeyboardButton(text="📋 Мои заявки", callback_data="my_issues")],
                    [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")]
                ])
                
                # Формируем и проверяем длину сообщения
                message_text = (
                    "✅ Регистрация завершена!\n\n"
                    f"👤 ФИО: {updated_user.full_name}\n"
                    f"📱 Телефон: {updated_user.phone}"
                    f"{contact_info}\n\n"
                    "Теперь вы можете создавать заявки:"
                )
                
                # Проверяем длину и обрезаем при необходимости
                if len(message_text) > 4000:
                    contact_info_short = "\n🔗 Контакт создан"
                    message_text = (
                        "✅ Регистрация завершена!\n\n"
                        f"👤 ФИО: {updated_user.full_name}\n"
                        f"📱 Телефон: {updated_user.phone}"
                        f"{contact_info_short}\n\n"
                        "Теперь вы можете создавать заявки:"
                    )
                
                await message.answer(message_text, reply_markup=keyboard)
                await state.clear()  # Очищаем состояние только для физических лиц
            else:
                await message.answer("❌ Ошибка при сохранении данных. Попробуйте снова.")
        
    elif user_type == "legal":
        # Для юридических лиц переходим к вводу ИНН
        await message.answer(
            "🏢 Теперь введите ИНН вашей компании:"
        )
        await state.set_state(RegistrationStates.waiting_for_inn)

@router.message(StateFilter(RegistrationStates.waiting_for_inn))
async def process_inn(message: Message, state: FSMContext):
    """
    Обработка ИНН, поиск компании и переход к выбору объекта обслуживания
    """
    inn = message.text.strip() if message.text else None
    
    if not inn or not inn.isdigit() or len(inn) not in [10, 12]:
        await message.answer(
            "❌ Неверный формат ИНН.\n"
            "ИНН юридического лица должен содержать 10 цифр.\n"
            "ИНН индивидуального предпринимателя должен содержать 12 цифр.\n\n"
            "Пожалуйста, введите корректный ИНН:"
        )
        return
    
    okdesk_api = OkdeskAPI()
    
    try:
        # Поиск пользователя в БД
        user = UserService.get_user_by_telegram_id(message.from_user.id)
        
        if not user:
            await message.answer("❌ Пользователь не найден. Начните регистрацию заново.")
            await state.clear()
            return
        
        # Получаем данные из состояния
        data = await state.get_data()
        
        await message.answer(f"🔍 Проверяю ИНН {inn} и ищу компанию в базе Okdesk...")
        
        # Поиск компании по ИНН в Okdesk
        company = await okdesk_api.find_company_by_inn(inn, create_if_not_found=False)
        
        if company and 'id' in company:
            # Компания найдена
            company_id = company['id']
            company_name = company.get('name', f"Компания (ИНН: {inn})")
            
            await message.answer(
                f"✅ Компания найдена: {company_name}\n"
                "🏢 Теперь выберите объект обслуживания (филиал/отдел):"
            )
            
            # Сохраняем данные компании в состоянии для следующего шага
            await state.update_data(
                company_id=company_id,
                company_name=company_name,
                inn=inn
            )
            
            # Получаем доступные объекты обслуживания
            service_objects = await get_available_service_objects(okdesk_api, company_id)
            
            if service_objects:
                # Создаем клавиатуру с объектами обслуживания
                keyboard = InlineKeyboardMarkup(inline_keyboard=[])
                for obj in service_objects[:10]:  # Ограничиваем до 10 объектов
                    # Используем адрес вместо названия на кнопке
                    address = obj.get('address', obj.get('name', 'Адрес не указан'))
                    
                    # Улучшенная логика обрезания адреса - показываем значимую часть
                    if len(address) > 45:
                        # Пытаемся найти улицу и дом в адресе
                        parts = address.split(', ')
                        if len(parts) >= 3:
                            # Показываем последние части адреса (улица, дом)
                            street_parts = parts[-2:]
                            display_text = ', '.join(street_parts)
                            if len(display_text) > 45:
                                display_text = display_text[:42] + "..."
                        else:
                            display_text = address[:42] + "..."
                    else:
                        display_text = address
                    
                    keyboard.inline_keyboard.append([
                        InlineKeyboardButton(
                            text=f"📍 {display_text}",
                            callback_data=f"select_branch_{obj['id']}"
                        )
                    ])
                
                # Добавляем кнопку для ввода вручную
                keyboard.inline_keyboard.append([
                    InlineKeyboardButton(
                        text="✏️ Ввести название вручную",
                        callback_data="enter_branch_manual"
                    )
                ])
                
                await message.answer(
                    "Выберите объект обслуживания из списка или введите название вручную:",
                    reply_markup=keyboard
                )
                
                # Переходим в состояние ожидания выбора объекта обслуживания
                await state.set_state(RegistrationStates.waiting_for_branch)
            else:
                # Если объектов нет, предлагаем ввести вручную
                await message.answer(
                    "Объекты обслуживания не найдены.\n"
                    "Введите название объекта обслуживания (филиала/отдела):"
                )
                await state.set_state(RegistrationStates.waiting_for_branch)
        else:
            # Компания не найдена - переходим к ручному вводу объекта обслуживания
            await message.answer(
                f"⚠️ Компания с ИНН {inn} не найдена в системе.\n"
                "Введите название объекта обслуживания (филиала/отдела):"
            )
            # Сохраняем данные для дальнейшей обработки
            await state.update_data(
                company_id=None,
                company_name=None,
                inn=inn
            )
            await state.set_state(RegistrationStates.waiting_for_branch)
        
    except Exception as e:
        logger.error(f"Ошибка обработки ИНН: {e}")
        import traceback
        traceback.print_exc()
        
        # Создаем безопасное сообщение об ошибке
        error_message = f"❌ Произошла ошибка при обработке ИНН: {str(e)}\nПопробуйте снова или обратитесь к администратору."
        if len(error_message) > 4000:
            error_message = "❌ Произошла ошибка при обработке ИНН.\nПопробуйте снова или обратитесь к администратору."
        
        await message.answer(error_message)
    
    finally:
        await okdesk_api.close()

@router.callback_query(F.data.startswith("select_branch_"), StateFilter(RegistrationStates.waiting_for_branch))
async def process_branch_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора объекта обслуживания из списка"""
    branch_id = int(callback.data.replace("select_branch_", ""))
    
    # Получаем данные из состояния
    data = await state.get_data()
    company_id = data.get("company_id")
    
    # Получаем название объекта по ID
    branch_name = await get_service_object_name_by_id(callback, branch_id, company_id)
    
    await callback.message.edit_text(
        f"✅ Выбран объект обслуживания: {branch_name}\n"
        "🔗 Завершаю регистрацию..."
    )
    
    # Завершаем регистрацию с выбранным объектом обслуживания
    await finalize_legal_registration(callback, state, branch_name)

@router.callback_query(F.data == "enter_branch_manual", StateFilter(RegistrationStates.waiting_for_branch))
async def enter_branch_manual(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора ручного ввода объекта обслуживания"""
    await callback.message.edit_text(
        "🏢 Введите название объекта обслуживания (филиала/отдела):"
    )
    await state.set_state(RegistrationStates.waiting_for_branch)

@router.message(StateFilter(RegistrationStates.waiting_for_branch))
async def process_manual_branch_input(message: Message, state: FSMContext):
    """Обработка ручного ввода названия объекта обслуживания"""
    branch_name = message.text.strip()
    
    if not branch_name:
        await message.answer("❌ Название объекта не может быть пустым. Введите название:")
        return
    
    await message.answer(
        f"✅ Объект обслуживания: {branch_name}\n"
        "🔗 Завершаю регистрацию..."
    )
    
    # Завершаем регистрацию с введенным объектом обслуживания
    await finalize_legal_registration(message, state, branch_name)

async def finalize_legal_registration(message_or_callback, state: FSMContext, service_object_name: str):
    """Финализация регистрации юридического лица с объектом обслуживания"""
    # Получаем данные из состояния
    data = await state.get_data()
    user = UserService.get_user_by_telegram_id(message_or_callback.from_user.id)
    
    if not user:
        error_msg = "❌ Пользователь не найден. Начните регистрацию заново."
        if hasattr(message_or_callback, 'message'):
            await message_or_callback.answer()
            await message_or_callback.bot.send_message(
                chat_id=message_or_callback.message.chat.id,
                text=error_msg
            )
        else:
            await message_or_callback.answer(error_msg)
        await state.clear()
        return
    
    company_id = data.get("company_id")
    company_name = data.get("company_name", "Не найдена в системе")
    inn = data.get("inn")
    full_name = data.get("full_name")
    phone = data.get("phone")
    
    okdesk_api = OkdeskAPI()
    
    try:
        # Сохраняем данные пользователя с привязкой к компании и объекту обслуживания
        updated_user = UserService.update_user_legal(
            user_id=user.id,
            inn_company=inn,
            company_id=company_id,
            company_name=company_name,
            service_object_name=service_object_name
        )
        
        if updated_user:
            # Создаем контакт с привязкой к компании (если найдена)
            try:
                # Правильно разбираем ФИО: Фамилия Имя Отчество
                name_parts = full_name.split(' ')
                if len(name_parts) >= 2:
                    last_name = name_parts[0]  # Фамилия
                    first_name = name_parts[1]  # Имя
                    patronymic = name_parts[2] if len(name_parts) > 2 else ""  # Отчество
                else:
                    first_name = full_name
                    last_name = "Представитель"
                    patronymic = ""
                
                # Используем новую функцию с доступом к порталу
                contact_response = await okdesk_api.create_contact_with_portal_access(
                    first_name=first_name,
                    last_name=last_name,
                    patronymic=patronymic,
                    phone=phone,
                    company_id=company_id,
                    position="Представитель компании",
                    telegram_username=message_or_callback.from_user.username,
                    inn_company=inn,
                    comment=f"Контактное лицо компании. ИНН: {inn}. Объект обслуживания: {service_object_name}. Создан из Telegram бота (ID: {message_or_callback.from_user.id})",
                    # Параметры доступа к порталу
                    access_level=[
                        'company_issues',  # Отображать заявки компании
                        'allow_close_company_issues'  # Разрешить закрывать заявки компании
                    ]
                )
                
                # Обработка ответа создания контакта
                contact_info = ""
                if contact_response and 'id' in contact_response:
                    contact_id = contact_response['id']
                    auth_code = contact_response.get('authentication_code')
                    
                    # Сохраняем ID контакта и код авторизации
                    UserService.update_user_contact_info(
                        user_id=updated_user.id,
                        contact_id=contact_id,
                        auth_code=auth_code
                    )
                    
                    if auth_code:
                        contact_info = (f"\n🔗 Контакт создан (ID: {contact_id})\n"
                                      f"🔐 Код: {auth_code}\n"
                                      f"🌐 Портал: {config.OKDESK_PORTAL_URL}")
                    else:
                        contact_info = f"\n🔗 Контакт создан (ID: {contact_id})"
                elif contact_response and contact_response.get('error') == 422:
                    # Контакт уже существует
                    contact_info = "\n⚠️ Контакт уже существует"
                    contact_info += f"\n🌐 Портал: {config.OKDESK_PORTAL_URL}"
                else:
                    contact_info = "\n⚠️ Ошибка создания контакта"
                    
            except Exception as e:
                logger.error(f"Ошибка создания контакта в Okdesk: {e}")
                contact_info = "\n⚠️ Ошибка создания контакта"
            
            # Создаем клавиатуру с кнопками быстрого доступа
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 Создать заявку", callback_data="create_issue")],
                [InlineKeyboardButton(text="📋 Мои заявки", callback_data="my_issues")],
                [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")]
            ])
            
            # Формируем сообщение и проверяем длину
            message_text = (
                "✅ Регистрация завершена!\n\n"
                f"👤 {full_name}\n"
                f"📱 {phone}\n"
                f"🏢 {company_name}\n"
                f"📍 {service_object_name}\n"
                f"🔢 ИНН: {inn}"
                f"{contact_info}\n\n"
                "Теперь можно создавать заявки:"
            )
            
            logger.info(f"Длина contact_info: {len(contact_info)} символов")
            logger.info(f"Длина полного сообщения: {len(message_text)} символов")
            
            # Telegram лимит 4096 символов, оставляем запас
            if len(message_text) > 4000:
                logger.warning(f"Сообщение слишком длинное ({len(message_text)} символов), обрезаем contact_info")
                # Используем короткую версию contact_info
                contact_info_short = "\n🔗 Контакт создан"
                message_text = (
                    "✅ Регистрация завершена!\n\n"
                    f"👤 {full_name}\n"
                    f"📱 {phone}\n"
                    f"🏢 {company_name}\n"
                    f"📍 {service_object_name}\n"
                    f"🔢 ИНН: {inn}"
                    f"{contact_info_short}\n\n"
                    "Теперь можно создавать заявки:"
                )
                logger.info(f"Сообщение после обрезания: {len(message_text)} символов")
            
            # Финальная проверка на всякий случай
            if len(message_text) > 4096:
                logger.error(f"Сообщение все еще слишком длинное: {len(message_text)} символов")
                message_text = "✅ Регистрация завершена!\n\nТеперь можно создавать заявки:"
            
            logger.info(f"Отправляем сообщение длиной {len(message_text)} символов")
            # Отправляем сообщение в зависимости от типа message_or_callback
            if hasattr(message_or_callback, 'message'):
                # Это CallbackQuery - сначала отвечаем на callback
                await message_or_callback.answer()
                # Затем отправляем сообщение
                await message_or_callback.bot.send_message(
                    chat_id=message_or_callback.message.chat.id,
                    text=message_text,
                    reply_markup=keyboard
                )
            else:
                # Это Message
                await message_or_callback.answer(message_text, reply_markup=keyboard)
        else:
            error_msg = "❌ Ошибка при сохранении данных. Попробуйте снова."
            if hasattr(message_or_callback, 'message'):
                await message_or_callback.answer()
                await message_or_callback.bot.send_message(
                    chat_id=message_or_callback.message.chat.id,
                    text=error_msg
                )
            else:
                await message_or_callback.answer(error_msg)
    
    except Exception as e:
        logger.error(f"Ошибка финализации регистрации: {e}")
        import traceback
        traceback.print_exc()
        
        # Создаем безопасное сообщение об ошибке
        error_message = f"❌ Произошла ошибка при регистрации: {str(e)}\nПопробуйте снова или обратитесь к администратору."
        # Обрезаем если слишком длинное
        if len(error_message) > 4000:
            error_message = "❌ Произошла ошибка при регистрации.\nПопробуйте снова или обратитесь к администратору."
        
        # Отправляем сообщение об ошибке в зависимости от типа
        if hasattr(message_or_callback, 'message'):
            # Это CallbackQuery - сначала отвечаем на callback
            await message_or_callback.answer()
            # Затем отправляем сообщение
            await message_or_callback.bot.send_message(
                chat_id=message_or_callback.message.chat.id,
                text=error_message
            )
        else:
            # Это Message
            await message_or_callback.answer(error_message)
    
    finally:
        await okdesk_api.close()
    
    await state.clear()

async def get_service_object_name_by_id(callback_or_message, branch_id: int, company_id: int) -> str:
    """Получить название объекта обслуживания по ID"""
    try:
        okdesk_api = OkdeskAPI()
        
        # Сначала пробуем получить из maintenance_entities
        maintenance_entities = await okdesk_api._make_request('GET', 'maintenance_entities')
        if maintenance_entities and isinstance(maintenance_entities, list):
            for obj in maintenance_entities:
                if obj.get('id') == branch_id:
                    await okdesk_api.close()
                    return obj.get('name', f'Объект {branch_id}')
        
        # Если не нашли, пробуем из issues
        issues = await okdesk_api._make_request('GET', 'issues/list')
        if issues and isinstance(issues, list):
            for issue in issues:
                company = issue.get('company', {})
                service_obj = issue.get('service_object', {})
                if (isinstance(company, dict) and company.get('id') == company_id and 
                    isinstance(service_obj, dict) and service_obj.get('id') == branch_id):
                    await okdesk_api.close()
                    return service_obj.get('name', f'Объект {branch_id}')
        
        await okdesk_api.close()
        return f'Объект {branch_id}'
        
    except Exception as e:
        logger.error(f"Ошибка получения названия объекта обслуживания: {e}")
        return f'Объект {branch_id}'

def get_user_type_text(user_type: str) -> str:
    """Получить текстовое описание типа пользователя"""
    if user_type == "physical":
        return "Физическое лицо"
    elif user_type == "legal":
        return "Юридическое лицо"
    return "Не определено"