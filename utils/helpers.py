import re
from typing import Optional

def validate_phone(phone: str) -> bool:
    """Валидация номера телефона"""
    # Убираем все символы кроме цифр и +
    clean_phone = re.sub(r'[^\d+]', '', phone)
    
    # Проверяем российские номера
    if clean_phone.startswith('+7') and len(clean_phone) == 12:
        return True
    if clean_phone.startswith('8') and len(clean_phone) == 11:
        return True
    if clean_phone.startswith('7') and len(clean_phone) == 11:
        return True
    
    return False

def normalize_phone(phone: str) -> str:
    """Нормализация номера телефона к формату +7XXXXXXXXXX"""
    # Убираем все символы кроме цифр
    digits = re.sub(r'\D', '', phone)
    
    # Преобразуем к единому формату
    if digits.startswith('8') and len(digits) == 11:
        return '+7' + digits[1:]
    elif digits.startswith('7') and len(digits) == 11:
        return '+' + digits
    elif len(digits) == 10:
        return '+7' + digits
    
    return phone

def validate_inn(inn: str) -> bool:
    """Валидация ИНН"""
    # Убираем все символы кроме цифр
    clean_inn = re.sub(r'\D', '', inn)
    
    # ИНН должен быть 10 или 12 цифр
    if len(clean_inn) not in [10, 12]:
        return False
    
    # Простая проверка контрольных сумм для российских ИНН
    if len(clean_inn) == 10:
        return validate_inn_10(clean_inn)
    elif len(clean_inn) == 12:
        return validate_inn_12(clean_inn)
    
    return False

def validate_inn_10(inn: str) -> bool:
    """Валидация 10-значного ИНН (юридические лица)"""
    coefficients = [2, 4, 10, 3, 5, 9, 4, 6, 8]
    
    try:
        digits = [int(d) for d in inn]
        check_sum = sum(coef * digit for coef, digit in zip(coefficients, digits[:9])) % 11
        check_sum = check_sum % 10
        return check_sum == digits[9]
    except (ValueError, IndexError):
        return False

def validate_inn_12(inn: str) -> bool:
    """Валидация 12-значного ИНН (физические лица)"""
    coefficients_1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    coefficients_2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    
    try:
        digits = [int(d) for d in inn]
        
        # Проверка первой контрольной суммы
        check_sum_1 = sum(coef * digit for coef, digit in zip(coefficients_1, digits[:10])) % 11
        check_sum_1 = check_sum_1 % 10
        
        # Проверка второй контрольной суммы
        check_sum_2 = sum(coef * digit for coef, digit in zip(coefficients_2, digits[:11])) % 11
        check_sum_2 = check_sum_2 % 10
        
        return check_sum_1 == digits[10] and check_sum_2 == digits[11]
    except (ValueError, IndexError):
        return False

def format_datetime(dt) -> str:
    """Форматирование даты и времени для пользователя"""
    if not dt:
        return "Не указано"
    
    return dt.strftime("%d.%m.%Y в %H:%M")

def truncate_text(text: str, max_length: int = 100) -> str:
    """Обрезка текста с добавлением многоточия"""
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."

def escape_html(text: str) -> str:
    """Экранирование HTML символов для Telegram"""
    if not text:
        return ""
    
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def extract_issue_id_from_url(url: str) -> Optional[int]:
    """Извлечение ID заявки из URL Okdesk"""
    pattern = r'/issues/(\d+)'
    match = re.search(pattern, url)
    return int(match.group(1)) if match else None

def create_user_mention(user_id: int, username: str = None, full_name: str = None) -> str:
    """Создание упоминания пользователя для логов"""
    if username:
        return f"@{username} (ID: {user_id})"
    elif full_name:
        return f"{full_name} (ID: {user_id})"
    else:
        return f"User {user_id}"

def format_issue_status(status: str) -> str:
    """Форматирование статуса заявки с эмодзи"""
    status_map = {
        "opened": "🟡 Открыта",
        "in_progress": "🔵 В работе",
        "on_hold": "⏸️ Приостановлена",
        "resolved": "✅ Решена",
        "closed": "🔒 Закрыта",
        "cancelled": "❌ Отменена"
    }
    
    return status_map.get(status.lower(), f"📋 {status}")

def create_issue_title(description: str) -> str:
    """Создание краткого заголовка из описания заявки"""
    if not description:
        return "Новая заявка"
    
    # Убираем лишние пробелы и переносы строк
    clean_description = ' '.join(description.strip().split())
    
    # Если описание короткое, используем его целиком
    if len(clean_description) <= 50:
        return clean_description
    
    # Пытаемся найти окончание первого предложения
    sentences = clean_description.split('.')
    if sentences and len(sentences[0]) <= 50:
        return sentences[0].strip()
    
    # Ищем запятую или другие знаки препинания
    for punct in [',', ';', ':', '!', '?']:
        parts = clean_description.split(punct)
        if parts and len(parts[0]) <= 50:
            return parts[0].strip()
    
    # Если ничего не подошло, обрезаем по словам
    words = clean_description.split()
    title = ""
    for word in words:
        if len(title + word) > 47:  # Оставляем место для "..."
            break
        title += word + " "
    
    return title.strip() + "..."

def validate_env_variables() -> list:
    """Проверка обязательных переменных окружения"""
    import os
    
    required_vars = [
        'BOT_TOKEN',
        'OKDESK_API_URL',
        'OKDESK_API_TOKEN'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    return missing_vars
