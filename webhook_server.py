from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
import hmac
import hashlib
from database.crud import IssueService, CommentService, UserService
from models.database import create_tables
from services.okdesk_api import OkdeskAPI
import config

# Инициализируем базу данных при запуске (подключаемся к общей базе)
try:
    if create_tables():
        print("✅ Webhook сервер подключен к общей базе данных")
    else:
        print("⚠️ Проблемы с базой данных, но продолжаем работу")
except Exception as e:
    print(f"❌ Критическая ошибка базы данных: {e}")
    # Не останавливаем сервер, продолжаем работу

app = FastAPI()

@app.get("/")
async def root():
    """Корневой endpoint для проверки работы сервера"""
    return {"message": "Okdesk Bot Webhook Server is running", "status": "ok"}

@app.get(config.WEBHOOK_PATH)
async def webhook_info():
    """Информация о webhook endpoint"""
    return {"message": "Webhook endpoint is ready", "path": config.WEBHOOK_PATH}

class WebhookData(BaseModel):
    """Модель данных вебхука"""
    event: str
    data: Dict[str, Any]
    timestamp: Optional[int] = None

@app.post(config.WEBHOOK_PATH)
async def webhook_handler(request: Request):
    """Обработчик вебхуков от Okdesk"""
    
    try:
        # Получаем тело запроса
        body = await request.body()
        print(f"🎣 Получен webhook (raw): {body.decode('utf-8')}")
        
        # Пробуем парсить JSON
        try:
            data = json.loads(body.decode('utf-8'))
            print(f"📄 Parsed JSON: {json.dumps(data, indent=2, ensure_ascii=False)}")
        except Exception as e:
            print(f"❌ Ошибка парсинга JSON: {e}")
            return {"message": "Webhook received", "error": "Invalid JSON"}
        
        # Проверяем подпись вебхука (только если настроен секретный ключ)
        if config.WEBHOOK_SECRET and config.WEBHOOK_SECRET.strip():
            signature = request.headers.get("X-Okdesk-Signature")
            if not verify_webhook_signature(body, signature):
                raise HTTPException(status_code=403, detail="Invalid signature")
        
        # Определяем тип события
        event = data.get("event", "unknown")
        if isinstance(event, dict):
            event = event.get("event_type", "unknown")
        
        event_data = data.get("data", data)
        
        print(f"📊 Event: {event}")
        
        try:
            if event == "issue.created" or event == "new_ticket":
                await handle_issue_created(data.get("issue", event_data))
            elif event == "issue.updated":
                await handle_issue_updated(event_data)
            elif event == "comment.created" or event == "new_comment":
                await handle_comment_created(data)
            elif event == "issue.status_changed":
                await handle_status_changed(event_data)
            else:
                print(f"❓ Unknown event: {event}")
                # Пробуем обработать как комментарий, если есть признаки
                if "comment" in str(data).lower() or "content" in data:
                    print("🔄 Пробуем обработать как комментарий...")
                    await handle_comment_created(data)
            
            return {"status": "success", "event": event}
        
        except Exception as e:
            print(f"❌ Webhook processing error: {e}")
            return {"status": "error", "message": str(e)}
    
    except Exception as e:
        print(f"❌ Request processing error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def handle_issue_created(data: Dict[str, Any]):
    """Обработка создания заявки"""
    issue_id = data.get("id")
    if not issue_id:
        return
    
    # Проверяем, есть ли такая заявка в нашей БД
    issue = IssueService.get_issue_by_okdesk_id(issue_id)
    if issue:
        print(f"Issue {issue_id} already exists in database")
        return
    
    print(f"New issue created in Okdesk: {issue_id}")

async def handle_issue_updated(data: Dict[str, Any]):
    """Обработка обновления заявки"""
    print(f"🔄 Обработка обновления заявки: {json.dumps(data, indent=2, ensure_ascii=False)}")

    issue_id = data.get("id")
    if not issue_id:
        print("❌ Не найден ID заявки в данных обновления")
        return

    # Находим заявку в нашей БД
    issue = IssueService.get_issue_by_okdesk_id(issue_id)
    if not issue:
        print(f"❌ Заявка {issue_id} не найдена в базе данных")
        return

    # Обновляем статус, если изменился
    new_status = data.get("status")
    if new_status and new_status != issue.status:
        print(f"📊 Статус заявки {issue_id} изменился: {issue.status} -> {new_status}")

        updated_issue = IssueService.update_issue_status(issue.id, new_status)
        if updated_issue:
            print(f"✅ Статус заявки {issue_id} обновлен в БД")

            # Уведомляем пользователя о смене статуса
            await notify_user_status_change(updated_issue, new_status, issue.status)
            print(f"✅ Пользователь уведомлен об изменении статуса")
        else:
            print(f"❌ Не удалось обновить статус заявки {issue_id} в БД")
    else:
        print(f"ℹ️ Статус заявки {issue_id} не изменился или не указан")

    print(f"Issue {issue_id} updated")

async def handle_comment_created(data: Dict[str, Any]):
    """Обработка создания комментария"""
    print(f"🔍 Полные данные комментария: {json.dumps(data, indent=2, ensure_ascii=False)}")
    
    # Извлекаем данные из структуры webhook
    event_data = data.get("event", data)
    issue_data = data.get("issue", {})
    comment_data = event_data.get("comment", {})
    author_data = event_data.get("author", {})
    
    # Получаем ID и содержимое
    issue_id = issue_data.get("id")
    comment_id = comment_data.get("id")
    content = comment_data.get("content")
    
    # Формируем имя автора
    author_name = "Неизвестен"
    if author_data:
        first_name = author_data.get("first_name", "")
        last_name = author_data.get("last_name", "")
        author_name = f"{first_name} {last_name}".strip()
    
    print(f"📝 Получен комментарий:")
    print(f"   🎫 Заявка ID: {issue_id}")
    print(f"   💬 Комментарий ID: {comment_id}")
    print(f"   📄 Содержимое: {content}")
    print(f"   👤 Автор: {author_name}")
    
    if not all([issue_id, comment_id, content]):
        print("❌ Недостаточно данных для обработки комментария")
        return
    
    # Находим заявку в нашей БД
    issue = IssueService.get_issue_by_okdesk_id(issue_id)
    if not issue:
        print(f"❌ Заявка {issue_id} не найдена в базе данных")
        
        # Отладочная информация
        print(f"🔍 Ищем в базе данных по пути: {config.DATABASE_URL}")
        all_issues = IssueService.get_all_issues()
        print(f"📊 Всего заявок в БД: {len(all_issues)}")
        if all_issues:
            print("📋 Последние заявки в БД:")
            for i in all_issues[-3:]:  # Показываем последние 3
                print(f"   - ID: {i.okdesk_issue_id}, Title: {i.title}")
        
        return
    
    print(f"✅ Заявка найдена в БД: {issue.title}")
    
    # Проверяем, не наш ли это комментарий (чтобы избежать дублирования)
    existing_comments = CommentService.get_issue_comments(issue.id)
    for comment in existing_comments:
        if comment.okdesk_comment_id == comment_id:
            print(f"⚠️ Комментарий {comment_id} уже существует")
            return
    
    # Добавляем комментарий в БД
    CommentService.add_comment(
        issue_id=issue.id,
        telegram_user_id=issue.telegram_user_id,
        content=content,
        okdesk_comment_id=comment_id,
        is_from_okdesk=True
    )
    
    print(f"✅ Комментарий добавлен в базу данных")
    
    # Проверяем, не является ли автор комментария создателем заявки
    # Если да, то не отправляем уведомление (чтобы избежать спама собственными комментариями)
    author_contact_id = author_data.get("id")
    issue_creator = UserService.get_user_by_telegram_id(issue.telegram_user_id)
    
    if issue_creator and issue_creator.okdesk_contact_id and author_contact_id:
        if issue_creator.okdesk_contact_id == author_contact_id:
            print(f"⚠️ Комментарий оставлен создателем заявки ({author_name}), уведомление не отправляется")
            print(f"New comment from issue creator: {comment_id}")
            return
    
    # Уведомляем пользователя о новом комментарии
    await notify_user_new_comment(issue, content, author_data)
    print(f"✅ Пользователь уведомлен о новом комментарии")
    
    print(f"New comment from Okdesk: {comment_id}")

async def handle_status_changed(data: Dict[str, Any]):
    """Обработка смены статуса заявки"""
    print(f"🔄 Обработка изменения статуса: {json.dumps(data, indent=2, ensure_ascii=False)}")

    # Пробуем разные форматы данных
    issue_id = (
        data.get("issue_id") or
        data.get("id") or
        data.get("issue", {}).get("id")
    )

    new_status = (
        data.get("new_status") or
        data.get("status") or
        data.get("issue", {}).get("status")
    )

    old_status = (
        data.get("old_status") or
        data.get("previous_status") or
        data.get("old_status")
    )

    if not issue_id or not new_status:
        print(f"❌ Недостаточно данных для изменения статуса: issue_id={issue_id}, new_status={new_status}")
        return

    print(f"📊 Изменение статуса заявки {issue_id}: {old_status or 'неизвестен'} -> {new_status}")

    # Находим заявку в нашей БД
    issue = IssueService.get_issue_by_okdesk_id(issue_id)
    if not issue:
        print(f"❌ Заявка {issue_id} не найдена в базе данных")
        return

    # Обновляем статус в БД
    updated_issue = IssueService.update_issue_status(issue.id, new_status)
    if updated_issue:
        print(f"✅ Статус заявки {issue_id} обновлен в БД: {new_status}")

        # Уведомляем пользователя
        await notify_user_status_change(updated_issue, new_status, old_status)
        print(f"✅ Пользователь уведомлен об изменении статуса")
    else:
        print(f"❌ Не удалось обновить статус заявки {issue_id} в БД")

    print(f"Status changed for issue {issue_id}: {old_status or 'unknown'} -> {new_status}")

async def notify_user_status_change(issue, new_status: str, old_status: str = None):
    """Уведомление пользователя о смене статуса"""
    from bot import bot  # Импортируем бота
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from database.crud import IssueService
    
    status_text = config.ISSUE_STATUS_MESSAGES.get(new_status, new_status)
    
    message = (
        f"📊 Статус заявки #{issue.issue_number} изменился\n\n"
        f"📝 {issue.title}\n"
        f"🔄 Новый статус: {status_text}"
    )
    
    if old_status:
        old_status_text = config.ISSUE_STATUS_MESSAGES.get(old_status, old_status)
        message += f"\n⬅️ Предыдущий статус: {old_status_text}"
    
    # Создаем клавиатуру
    keyboard_buttons = []
    
    # Если статус изменился на "resolved" (решена), добавляем запрос оценки качества
    if new_status == "resolved":
        message += "\n\n⭐ Пожалуйста, оцените качество выполненной работы:"
        keyboard_buttons.extend([
            [InlineKeyboardButton(text="⭐⭐⭐⭐⭐ Отлично", callback_data=f"rate_5_{issue.id}")],
            [InlineKeyboardButton(text="⭐⭐⭐⭐ Хорошо", callback_data=f"rate_4_{issue.id}")],
            [InlineKeyboardButton(text="⭐⭐⭐ Нормально", callback_data=f"rate_3_{issue.id}")],
            [InlineKeyboardButton(text="⭐⭐ Плохо", callback_data=f"rate_2_{issue.id}")],
            [InlineKeyboardButton(text="⭐ Ужасно", callback_data=f"rate_1_{issue.id}")]
        ])
    
    # Добавляем стандартные кнопки
    keyboard_buttons.append([
        InlineKeyboardButton(text="🔗 Открыть в портале", url=issue.okdesk_url),
        InlineKeyboardButton(text="💬 Добавить комментарий в портале", url=issue.okdesk_url)
    ])
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="📋 Мои заявки", callback_data="my_issues"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    # Пытаемся обновить существующее сообщение о заявке
    message_updated = False
    if issue.telegram_message_id:
        try:
            await bot.edit_message_text(
                chat_id=issue.telegram_user_id,
                message_id=issue.telegram_message_id,
                text=message,
                reply_markup=keyboard
            )
            print(f"✅ Обновлено существующее сообщение о заявке {issue.id} (message_id={issue.telegram_message_id})")
            message_updated = True
        except Exception as e:
            print(f"⚠️ Не удалось обновить существующее сообщение: {e}")
    
    # Если не удалось обновить существующее сообщение, отправляем новое уведомление
    if not message_updated:
        try:
            sent_message = await bot.send_message(
                chat_id=issue.telegram_user_id,
                text=message,
                reply_markup=keyboard
            )
            
            # Сохраняем ID нового сообщения для будущих обновлений
            if sent_message and sent_message.message_id:
                IssueService.update_issue_message_id(issue.id, sent_message.message_id)
                print(f"✅ Отправлено новое уведомление и сохранен message_id={sent_message.message_id} для заявки {issue.id}")
            else:
                print(f"✅ Отправлено новое уведомление о смене статуса для заявки {issue.id}")
        except Exception as e:
            print(f"❌ Failed to send status notification: {e}")

async def notify_user_new_comment(issue, content: str, author: Dict):
    """Уведомление пользователя о новом комментарии"""
    from bot import bot  # Импортируем бота
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    author_name = author.get("name", "Сотрудник")
    
    message = (
        f"💬 Новый комментарий к заявке #{issue.issue_number}\n\n"
        f"📝 {issue.title}\n"
        f"👤 От: {author_name}\n"
        f"💭 Комментарий: {content[:200]}{'...' if len(content) > 200 else ''}\n\n"
        f"🔗 Открыть в портале: {issue.okdesk_url}"
    )
    
    # Создаем клавиатуру с кнопками быстрого доступа
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Ответить", callback_data=f"add_comment_{issue.issue_number}")],
        [InlineKeyboardButton(text="📋 Мои заявки", callback_data="my_issues"),
         InlineKeyboardButton(text="📝 Создать заявку", callback_data="create_issue")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    print(f"📤 Отправка уведомления пользователю {issue.telegram_user_id} о комментарии к заявке #{issue.issue_number}")
    print(f"📝 Сообщение: {message[:100]}...")
    print(f"🔘 Кнопки: {[btn.text for row in keyboard.inline_keyboard for btn in row]}")
    
    try:
        await bot.send_message(
            chat_id=issue.telegram_user_id,
            text=message,
            reply_markup=keyboard
        )
        print(f"✅ Уведомление о комментарии отправлено пользователю {issue.telegram_user_id}")
    except Exception as e:
        print(f"❌ Failed to send comment notification: {e}")
        import traceback
        traceback.print_exc()

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Проверка подписи вебхука"""
    if not signature or not config.WEBHOOK_SECRET or not config.WEBHOOK_SECRET.strip():
        return False
    
    expected_signature = hmac.new(
        config.WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    
    # Отладочная информация о конфигурации
    print(f"🔍 WEBHOOK STARTUP: Используется база данных: {config.DATABASE_URL}")
    
    # Информация о безопасности webhook
    if config.WEBHOOK_SECRET and config.WEBHOOK_SECRET.strip():
        print("🔐 Webhook защищен секретным ключом")
    else:
        print("⚠️  Webhook работает БЕЗ проверки подписи (не рекомендуется для продакшена)")
    
    print(f"🚀 Запуск webhook сервера на {config.HOST}:{config.PORT}")
    uvicorn.run(app, host=config.HOST, port=config.PORT)
