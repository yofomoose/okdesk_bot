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
                        contact_info = f"\n🔗 Контакт создан в Okdesk (ID: {contact_response['id']})"
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
            else:
                await message.answer("❌ Ошибка при сохранении данных. Попробуйте снова.")
        
        await state.clear()
        
    elif user_type == "legal":
        # Для юридических лиц переходим к вводу ИНН
        await message.answer(
            "🏢 Теперь введите ИНН вашей компании:"
        )
        await state.set_state(RegistrationStates.waiting_for_inn)
    
    await state.clear()

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
    
    await message.answer("🔍 Ищем вашу компанию в системе...")
    
    # Ищем компанию по ИНН в Okdesk
    okdesk_api = OkdeskAPI()
    company = await okdesk_api.search_company_by_inn(inn)
    
    user = UserService.get_user_by_telegram_id(message.from_user.id)
    data = await state.get_data()  # Получаем ФИО и телефон из состояния
    
    if company:
        # Компания найдена
        if user:
            updated_user = UserService.update_user_legal(
                user_id=user.id,
                inn_company=inn,
                company_id=company.get("id"),
                company_name=company.get("name")
            )
            
            if updated_user:
                # Создаем контакт в Okdesk для представителя компании
                try:
                    name_parts = data.get("full_name", "").split(' ', 1)
                    first_name = name_parts[0] if name_parts else data.get("full_name", "")
                    last_name = name_parts[1] if len(name_parts) > 1 else "Клиент"
                    
                    contact_response = await okdesk_api.create_contact(
                        first_name=first_name,
                        last_name=last_name,
                        phone=data.get("phone", ""),
                        company_id=company.get("id"),
                        comment=f"Представитель компании, создан из Telegram бота (ID: {message.from_user.id})"
                    )
                    
                    if contact_response and 'id' in contact_response:
                        contact_info = f"\n🔗 Контакт создан в Okdesk (ID: {contact_response['id']})"
                    else:
                        contact_info = "\n⚠️ Контакт не удалось создать в Okdesk"
                        
                except Exception as e:
                    print(f"Ошибка создания контакта в Okdesk: {e}")
                    contact_info = "\n⚠️ Ошибка при создании контакта в Okdesk"
                
                await message.answer(
                    "✅ Регистрация завершена!\n\n"
                    f"👤 ФИО: {data.get('full_name', 'Не указано')}\n"
                    f"📱 Телефон: {data.get('phone', 'Не указан')}\n"
                    f"🏢 Компания: {company.get('name', 'Не указано')}\n"
                    f"🔢 ИНН: {inn}"
                    f"{contact_info}\n\n"
                    "Теперь вы можете создавать заявки. Используйте /menu для доступа к функциям."
                )
            else:
                await message.answer("❌ Ошибка при сохранении данных. Попробуйте снова.")
    else:
        # Компания не найдена
        if user:
            updated_user = UserService.update_user_legal(
                user_id=user.id,
                inn_company=inn,
                company_id=None,
                company_name=None
            )
            
            if updated_user:
                # Создаем контакт даже если компания не найдена
                try:
                    name_parts = data.get("full_name", "").split(' ', 1)
                    first_name = name_parts[0] if name_parts else data.get("full_name", "")
                    last_name = name_parts[1] if len(name_parts) > 1 else "Клиент"
                    
                    contact_response = await okdesk_api.create_contact(
                        first_name=first_name,
                        last_name=last_name,
                        phone=data.get("phone", ""),
                        comment=f"ИНН: {inn}, компания не найдена в системе. Создан из Telegram бота (ID: {message.from_user.id})"
                    )
                    
                    if contact_response and 'id' in contact_response:
                        contact_info = f"\n🔗 Контакт создан в Okdesk (ID: {contact_response['id']})"
                    else:
                        contact_info = "\n⚠️ Контакт не удалось создать в Okdesk"
                        
                except Exception as e:
                    print(f"Ошибка создания контакта в Okdesk: {e}")
                    contact_info = "\n⚠️ Ошибка при создании контакта в Okdesk"
                
                await message.answer(
                    "⚠️ Компания с указанным ИНН не найдена в системе.\n"
                    "Ваши данные сохранены, но может потребоваться дополнительная настройка.\n\n"
                    f"👤 ФИО: {data.get('full_name', 'Не указано')}\n"
                    f"📱 Телефон: {data.get('phone', 'Не указан')}\n"
                    f"🔢 ИНН: {inn}"
                    f"{contact_info}\n\n"
                    "Используйте /menu для доступа к функциям."
                )
            else:
                await message.answer("❌ Ошибка при сохранении данных. Попробуйте снова.")
            
            if updated_user:
                await message.answer(
                    "⚠️ Компания с указанным ИНН не найдена в системе.\n"
                    "Ваши данные сохранены, но может потребоваться дополнительная настройка.\n\n"
                    f"🔢 ИНН: {inn}\n\n"
                    "Используйте /menu для доступа к функциям."
                )
            else:
                await message.answer("❌ Ошибка при сохранении данных. Попробуйте снова.")
    
    await okdesk_api.close()
    await state.clear()

def get_user_type_text(user_type: str) -> str:
    """Получить текстовое описание типа пользователя"""
    if user_type == "physical":
        return "Физическое лицо"
    elif user_type == "legal":
        return "Юридическое лицо"
    return "Не определено"
