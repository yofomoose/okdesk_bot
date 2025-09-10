from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.crud import UserService, IssueService
from services.okdesk_api import OkdeskAPI
from utils.helpers import validate_phone, normalize_phone, validate_inn
import config

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

class RegistrationStates(StatesGroup):
    waiting_for_user_type = State()
    waiting_for_full_name = State()
    waiting_for_phone = State()
    waiting_for_inn = State()

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
                # Создаем контакт в Okdesk
                try:
                    okdesk_api = OkdeskAPI()
                    name_parts = updated_user.full_name.split(' ', 1)
                    first_name = name_parts[0] if name_parts else updated_user.full_name
                    last_name = name_parts[1] if len(name_parts) > 1 else "Клиент"
                    
                    contact_response = await okdesk_api.create_contact(
                        first_name=first_name,
                        last_name=last_name,
                        phone=updated_user.phone,
                        comment=f"Создан автоматически из Telegram бота (ID: {message.from_user.id})"
                    )
                    await okdesk_api.close()
                    
                    if contact_response and 'id' in contact_response:
                        # Сохраняем ID контакта и код авторизации
                        contact_id = contact_response['id']
                        auth_code = contact_response.get('authentication_code')
                        
                        UserService.update_user_contact_info(
                            user_id=updated_user.id,
                            contact_id=contact_id,
                            auth_code=auth_code
                        )
                        
                        if auth_code:
                            contact_info = f"\n🔗 Контакт создан в Okdesk (ID: {contact_id})\n🔐 Код авторизации: {auth_code}"
                        else:
                            contact_info = f"\n🔗 Контакт создан в Okdesk (ID: {contact_id})"
                    else:
                        contact_info = "\n⚠️ Контакт не удалось создать в Okdesk"
                        
                except Exception as e:
                    print(f"Ошибка создания контакта в Okdesk: {e}")
                    contact_info = "\n⚠️ Ошибка при создании контакта в Okdesk"
                
                # Создаем клавиатуру с кнопками быстрого доступа
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📝 Создать заявку", callback_data="create_issue")],
                    [InlineKeyboardButton(text="📋 Мои заявки", callback_data="my_issues")],
                    [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")]
                ])
                
                await message.answer(
                    "✅ Регистрация завершена!\n\n"
                    f"👤 ФИО: {updated_user.full_name}\n"
                    f"📱 Телефон: {updated_user.phone}"
                    f"{contact_info}\n\n"
                    "Теперь вы можете создавать заявки:",
                    reply_markup=keyboard
                )
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
    Обработка ИНН, поиск компании и регистрация пользователя
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
        company_name = None
        
        company = await okdesk_api.find_company_by_inn(inn, create_if_not_found=False)
        
        if company and 'id' in company:
            # Компания найдена
            company_id = company['id']
            company_name = company.get('name', f"Компания (ИНН: {inn})")
            
            await message.answer(
                f"✅ Компания найдена: {company_name}\n"
                "🔗 Привязываю вас к этой компании..."
            )
            
            # Сохраняем данные пользователя с привязкой к компании
            updated_user = UserService.update_user_legal(
                user_id=user.id,
                inn_company=inn,
                company_id=company_id,
                company_name=company_name
            )
            
            if updated_user:
                # Создаем контакт с привязкой к найденной компании
                try:
                    name_parts = data.get("full_name", "").split(' ', 1)
                    first_name = name_parts[0] if name_parts else data.get("full_name", "")
                    last_name = name_parts[1] if len(name_parts) > 1 else "Представитель"
                    
                    contact_response = await okdesk_api.create_contact(
                        first_name=first_name,
                        last_name=last_name,
                        phone=data.get("phone", ""),
                        company_id=company_id,
                        position="Представитель компании",
                        inn_company=inn,
                        comment=f"Контактное лицо компании. ИНН: {inn}. Создан из Telegram бота (ID: {message.from_user.id})"
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
                            contact_info = (f"\n🔗 Контакт создан в Okdesk (ID: {contact_id})\n"
                                          f"🔐 Код авторизации: {auth_code}\n"
                                          f"🌐 Веб-портал: https://yapomogu55.okdesk.ru")
                        else:
                            contact_info = f"\n🔗 Контакт создан в Okdesk (ID: {contact_id})"
                    else:
                        contact_info = "\n⚠️ Не удалось создать контакт в Okdesk"
                        
                except Exception as e:
                    print(f"Ошибка создания контакта в Okdesk: {e}")
                    contact_info = "\n⚠️ Ошибка при создании контакта в Okdesk"
                
                # Создаем клавиатуру с кнопками быстрого доступа
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📝 Создать заявку", callback_data="create_issue")],
                    [InlineKeyboardButton(text="📋 Мои заявки", callback_data="my_issues")],
                    [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")]
                ])
                
                await message.answer(
                    "✅ Регистрация юридического лица завершена!\n\n"
                    f"👤 ФИО: {data.get('full_name', 'Не указано')}\n"
                    f"📱 Телефон: {data.get('phone', 'Не указан')}\n"
                    f"🏢 Компания: {company_name}\n"
                    f"🔢 ИНН: {inn}"
                    f"{contact_info}\n\n"
                    "Теперь вы можете создавать заявки от имени компании:",
                    reply_markup=keyboard
                )
            else:
                await message.answer("❌ Ошибка при сохранении данных. Попробуйте снова.")
        else:
            # Компания не найдена - регистрируем без привязки к компании
            await message.answer(
                f"⚠️ Компания с ИНН {inn} не найдена в системе.\n"
                "Регистрирую вас как пользователя с указанием ИНН, но без привязки к компании."
            )
            
            # Сохраняем данные пользователя без привязки к компании
            updated_user = UserService.update_user_legal(
                user_id=user.id,
                inn_company=inn,
                company_id=None,
                company_name=None
            )
            
            if updated_user:
                # Создаем контакт без привязки к компании
                try:
                    name_parts = data.get("full_name", "").split(' ', 1)
                    first_name = name_parts[0] if name_parts else data.get("full_name", "")
                    last_name = name_parts[1] if len(name_parts) > 1 else "Представитель"
                    
                    contact_response = await okdesk_api.create_contact(
                        first_name=first_name,
                        last_name=last_name,
                        phone=data.get("phone", ""),
                        position="Представитель",
                        inn_company=inn,
                        comment=f"ИНН: {inn}. Создан из Telegram бота (ID: {message.from_user.id})"
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
                            contact_info = (f"\n🔗 Контакт создан в Okdesk (ID: {contact_id})\n"
                                          f"🔐 Код авторизации: {auth_code}\n"
                                          f"🌐 Веб-портал: https://yapomogu55.okdesk.ru")
                        else:
                            contact_info = f"\n🔗 Контакт создан в Okdesk (ID: {contact_id})"
                    else:
                        contact_info = "\n⚠️ Не удалось создать контакт в Okdesk"
                        
                except Exception as e:
                    print(f"Ошибка создания контакта в Okdesk: {e}")
                    contact_info = "\n⚠️ Ошибка при создании контакта в Okdesk"
                
                # Создаем клавиатуру с кнопками быстрого доступа
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📝 Создать заявку", callback_data="create_issue")],
                    [InlineKeyboardButton(text="📋 Мои заявки", callback_data="my_issues")],
                    [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")]
                ])
                
                await message.answer(
                    "✅ Регистрация пользователя завершена!\n\n"
                    f"👤 ФИО: {data.get('full_name', 'Не указано')}\n"
                    f"📱 Телефон: {data.get('phone', 'Не указан')}\n"
                    f"🔢 ИНН: {inn}"
                    f"{contact_info}\n\n"
                    "Теперь вы можете создавать заявки:",
                    reply_markup=keyboard
                )
            else:
                # Не удалось обновить данные пользователя
                await message.answer(
                    f"❌ Не удалось сохранить данные пользователя с ИНН {inn}.\n"
                    "Пожалуйста, попробуйте еще раз или обратитесь к администратору."
                )
        
    except Exception as e:
        print(f"Ошибка обработки ИНН: {e}")
        import traceback
        traceback.print_exc()
        await message.answer(
            f"❌ Произошла ошибка при обработке ИНН: {str(e)}\n"
            "Попробуйте снова или обратитесь к администратору."
        )
    
    finally:
        await okdesk_api.close()
    
    await state.clear()

def get_user_type_text(user_type: str) -> str:
    """Получить текстовое описание типа пользователя"""
    if user_type == "physical":
        return "Физическое лицо"
    elif user_type == "legal":
        return "Юридическое лицо"
    return "Не определено"
