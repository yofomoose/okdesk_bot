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
                
                await message.answer(
                    "✅ Регистрация завершена!\n\n"
                    f"👤 ФИО: {updated_user.full_name}\n"
                    f"📱 Телефон: {updated_user.phone}"
                    f"{contact_info}\n\n"
                    "Теперь вы можете создавать заявки. Используйте /menu для доступа к функциям."
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
    """Обработка ввода ИНН"""
    inn = message.text.strip()
    
    # Валидация ИНН
    if not validate_inn(inn):
        await message.answer(
            "❌ Неверный формат ИНН.\n"
            "ИНН должен содержать 10 или 12 цифр и быть корректным."
        )
        return
    
    await message.answer("🔍 Ищем компанию с указанным ИНН...")
    
    # Ищем компанию по ИНН
    okdesk_api = OkdeskAPI()
    user = UserService.get_user_by_telegram_id(message.from_user.id)
    data = await state.get_data()  # Получаем ФИО и телефон из состояния
    
    try:
        print(f"DEBUG: Поиск компании с ИНН {inn}")
        company = await okdesk_api.search_company_by_inn(inn)
        print(f"DEBUG: Результат поиска: {company}")
        
        if company:
            # Компания найдена в системе
            await message.answer(
                f"✅ Найдена компания: {company.get('name')}\n"
                "🔗 Создаю ваш контакт и привязываю к этой компании..."
            )
            
            if user:
                # Обновляем пользователя с данными найденной компании
                updated_user = UserService.update_user_legal(
                    user_id=user.id,
                    inn_company=inn,
                    company_id=company.get("id"),
                    company_name=company.get("name")
                )
                
                if updated_user:
                    # Создаем контакт в Okdesk и привязываем к найденной компании
                    try:
                        name_parts = data.get("full_name", "").split(' ', 1)
                        first_name = name_parts[0] if name_parts else data.get("full_name", "")
                        last_name = name_parts[1] if len(name_parts) > 1 else "Представитель"
                        
                        contact_response = await okdesk_api.create_contact(
                            first_name=first_name,
                            last_name=last_name,
                            phone=data.get("phone", ""),
                            company_id=company.get("id"),  # Привязываем к найденной компании
                            position="Представитель компании",
                            comment=f"Контактное лицо компании. ИНН: {inn}. Создан из Telegram бота (ID: {message.from_user.id})"
                        )
                        
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
                                contact_info = (f"\n� Контакт создан в Okdesk (ID: {contact_id})\n"
                                              f"🔐 Код авторизации: {auth_code}\n"
                                              f"🌐 Веб-портал: https://yapomogu55.okdesk.ru")
                            else:
                                contact_info = f"\n🔗 Контакт создан в Okdesk (ID: {contact_id})"
                        else:
                            contact_info = "\n⚠️ Не удалось создать контакт в Okdesk"
                            
                    except Exception as e:
                        print(f"Ошибка создания контакта в Okdesk: {e}")
                        contact_info = "\n⚠️ Ошибка при создании контакта в Okdesk"
                    
                    await message.answer(
                        "✅ Регистрация юридического лица завершена!\n\n"
                        f"👤 ФИО: {data.get('full_name', 'Не указано')}\n"
                        f"📱 Телефон: {data.get('phone', 'Не указан')}\n"
                        f"🏢 Компания: {company.get('name')}\n"
                        f"🔢 ИНН: {inn}"
                        f"{contact_info}\n\n"
                        "Теперь вы можете создавать заявки от имени компании.\n"
                        "Используйте /menu для доступа к функциям."
                    )
                else:
                    await message.answer("❌ Ошибка при сохранении данных. Попробуйте снова.")
        
        else:
            # Компания не найдена
            await message.answer(
                f"⚠️ Компания с ИНН {inn} не найдена в системе.\n"
                "Регистрирую вас как физическое лицо с указанием ИНН..."
            )
            
            if user:
                # Сохраняем как физлицо с ИНН
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
                        last_name = name_parts[1] if len(name_parts) > 1 else "Клиент"
                        
                        contact_response = await okdesk_api.create_contact(
                            first_name=first_name,
                            last_name=last_name,
                            phone=data.get("phone", ""),
                            comment=f"ИНН: {inn}. Создан из Telegram бота (ID: {message.from_user.id})"
                        )
                        
                        if contact_response and 'id' in contact_response:
                            contact_id = contact_response['id']
                            auth_code = contact_response.get('authentication_code')
                            
                            UserService.update_user_contact_info(
                                user_id=updated_user.id,
                                contact_id=contact_id,
                                auth_code=auth_code
                            )
                            
                            if auth_code:
                                contact_info = (f"\n🔗 Контакт создан в Okdesk (ID: {contact_id})\n"
                                              f"🔐 Код авторизации: {auth_code}")
                            else:
                                contact_info = f"\n🔗 Контакт создан в Okdesk (ID: {contact_id})"
                        else:
                            contact_info = "\n⚠️ Не удалось создать контакт в Okdesk"
                            
                    except Exception as e:
                        print(f"Ошибка создания контакта в Okdesk: {e}")
                        contact_info = "\n⚠️ Ошибка при создании контакта в Okdesk"
                    
                    await message.answer(
                        "✅ Регистрация завершена!\n\n"
                        f"👤 ФИО: {data.get('full_name', 'Не указано')}\n"
                        f"📱 Телефон: {data.get('phone', 'Не указан')}\n"
                        f"🔢 ИНН: {inn}"
                        f"{contact_info}\n\n"
                        "Используйте /menu для доступа к функциям."
                    )
                else:
                    await message.answer("❌ Ошибка при сохранении данных. Попробуйте снова.")
        
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
