from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
import hmac
import hashlib
from database.crud import IssueService, CommentService, UserService
from models.database import create_tables, Issue
from services.okdesk_api import OkdeskAPI
import config
import re

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
    
    print(f"🎣 Webhook received at {config.WEBHOOK_PATH}")
    
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
        print(f"📊 All data keys: {list(data.keys())}")
        print(f"📊 Event data keys: {list(event_data.keys())}")
        
        try:
            if event == "issue.created" or event == "new_ticket":
                print(f"🎫 Обработка создания заявки")
                await handle_issue_created(data.get("issue", event_data))
            elif event == "issue.updated":
                print(f"🔄 Обработка обновления заявки")
                await handle_issue_updated(data.get("issue", event_data))
            elif event == "issue.status_changed":
                print(f"� Обработка изменения статуса заявки")
                await handle_status_changed(data.get("issue", event_data))
            elif event == "comment.created" or event == "new_comment":
                print(f"� Обработка создания комментария")
                await handle_comment_created(data)
            else:
                print(f"❓ Неизвестное событие: {event}")
                print(f"📄 Данные события: {json.dumps(event_data, indent=2, ensure_ascii=False)}")
                
                # Анализируем структуру данных для автоматического определения типа события
                if "issue" in data and "status" in str(data.get("issue", {})):
                    print("🔄 Обнаружены данные о статусе заявки, обрабатываем как изменение статуса...")
                    await handle_status_changed(data.get("issue", event_data))
                elif "comment" in str(data).lower() or "content" in str(data).lower():
                    print("🔄 Обнаружены данные комментария, обрабатываем как комментарий...")
                    await handle_comment_created(data)
                elif "status" in str(data).lower() or "state" in str(data).lower():
                    print("🔄 Обнаружены данные статуса, обрабатываем как изменение статуса...")
                    await handle_status_changed(event_data)
            
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
    if isinstance(new_status, dict):
        new_status = new_status.get("code", new_status)
    
    print(f"🔍 Новый статус из webhook: {new_status} (тип: {type(new_status)})")
    print(f"🔍 Текущий статус в БД: {issue.status}")
    
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
    try:
        print(f"🔍 Полные данные комментария: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        # Извлекаем данные из структуры webhook
        event_data = data.get("event", data)
        issue_data = data.get("issue", {})
        comment_data = event_data.get("comment", {})
        author_data = event_data.get("author", {})
        
        print(f"🔍 event_data keys: {list(event_data.keys())}")
        print(f"🔍 issue_data keys: {list(issue_data.keys())}")
        print(f"🔍 comment_data keys: {list(comment_data.keys())}")
        
        # Получаем ID и содержимое
        issue_id = issue_data.get("id")
        comment_id = comment_data.get("id")
        content = comment_data.get("content")
        is_public = comment_data.get("is_public", False)  # По умолчанию считаем не публичным, если поле отсутствует
        
        # Обрабатываем разные форматы поля public
        if isinstance(is_public, str):
            is_public = is_public.lower() in ('true', '1', 'yes', 'on')
        elif is_public is None:
            is_public = False
        
        print(f"🔍 Поля comment_data: {list(comment_data.keys())}")
        print(f"🔍 Значение public (raw): {comment_data.get('is_public', 'NOT_SET')}")
        print(f"🔍 Значение public (processed): {is_public}")
        print(f"🔍 Тип значения public: {type(comment_data.get('is_public'))}")
        
        # Формируем имя автора
        author_name = "Неизвестен"
        if author_data:
            first_name = author_data.get("first_name", "")
            last_name = author_data.get("last_name", "")
            author_name = f"{first_name} {last_name}".strip()
        
        print(f"📝 Получен комментарий:")
        print(f"   🎫 Заявка ID: {issue_id}")
        print(f"   💬 Комментарий ID: {comment_id}")
        print(f"   📄 Содержимое (очищенное): {clean_html_content(content)[:100]}{'...' if len(clean_html_content(content)) > 100 else ''}")
        print(f"   👤 Автор: {author_name}")
        print(f"   🌐 Публичный: {is_public}")
        
        if not all([issue_id, comment_id, content]):
            print("❌ Недостаточно данных для обработки комментария")
            return
        
        # Проверяем, является ли комментарий публичным
        if not is_public:
            print(f"🔒 Комментарий {comment_id} является внутренним (не публичным), уведомление клиенту не отправляется")
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
        
        # Проверяем, изменился ли статус заявки при добавлении комментария
        current_status = issue_data.get("status")
        if isinstance(current_status, dict):
            current_status = current_status.get("code", current_status)
        
        if current_status and current_status != issue.status:
            print(f"📊 Статус заявки {issue_id} изменился при добавлении комментария: {issue.status} -> {current_status}")
            
            # Обновляем статус в БД
            updated_issue = IssueService.update_issue_status(issue.id, current_status)
            if updated_issue:
                print(f"✅ Статус заявки {issue_id} обновлен в БД через комментарий")
                
                # Уведомляем пользователя о смене статуса
                await notify_user_status_change(updated_issue, current_status, issue.status)
                print(f"✅ Пользователь уведомлен об изменении статуса через комментарий")
            else:
                print(f"❌ Не удалось обновить статус заявки {issue_id} в БД через комментарий")
        # Если да, то не отправляем уведомление (чтобы избежать спама собственными комментариями)
        author_contact_id = author_data.get("id")
        issue_creator = UserService.get_user_by_telegram_id(issue.telegram_user_id)
        
        if issue_creator and issue_creator.okdesk_contact_id and author_contact_id:
            if issue_creator.okdesk_contact_id == author_contact_id:
                print(f"⚠️ Комментарий оставлен создателем заявки ({author_name}), уведомление не отправляется")
                print(f"New comment from issue creator: {comment_id}")
                return
        
        # Проверяем, нужно ли отправлять уведомление о комментарии
        should_notify_comment = True
        
        # Если статус изменился на завершающий и комментарий от исполнителя, не отправляем уведомление о комментарии
        if current_status and current_status != issue.status:
            new_status_is_completion = current_status.lower() in config.RATING_REQUEST_STATUSES or any(s in current_status.lower() for s in config.RATING_REQUEST_STATUSES)
            if new_status_is_completion:
                # Проверяем, является ли автор комментария исполнителем заявки
                assignee_data = issue_data.get("assignee", {})
                assignee_employee = assignee_data.get("employee", {})
                assignee_id = assignee_employee.get("id")
                
                if assignee_id and author_contact_id == assignee_id:
                    print(f"⚠️ Комментарий при завершении от исполнителя ({author_name}), отдельное уведомление о комментарии не отправляется")
                    should_notify_comment = False
        
        if should_notify_comment:
            # Уведомляем пользователя о новом комментарии
            await notify_user_new_comment(issue, content, author_data)
            print(f"✅ Пользователь уведомлен о новом комментарии")
        else:
            print(f"ℹ️ Уведомление о комментарии пропущено (завершение от исполнителя)")
        
        print(f"New comment from Okdesk: {comment_id}")
        
    except Exception as e:
        print(f"❌ Ошибка при обработке комментария: {e}")
        import traceback
        traceback.print_exc()

async def handle_status_changed(data: Dict[str, Any]):
    """Обработка смены статуса заявки"""
    print(f"🔄 Обработка изменения статуса: {json.dumps(data, indent=2, ensure_ascii=False)}")

    # Пробуем разные форматы данных
    issue_id = (
        data.get("issue_id") or
        data.get("id") or
        data.get("issue", {}).get("id")
    )

    new_status_raw = (
        data.get("new_status") or
        data.get("status") or
        data.get("issue", {}).get("status") or
        data.get("status_id") or
        data.get("state")
    )

    old_status_raw = (
        data.get("old_status") or
        data.get("previous_status") or
        data.get("old_status") or
        data.get("previous_state")
    )
    
    # Обрабатываем статусы (могут быть объектами с полем 'code' или 'name')
    new_status = new_status_raw
    if isinstance(new_status_raw, dict):
        # Проверяем оба поля: code и name
        new_status = (
            new_status_raw.get("code") or
            new_status_raw.get("name") or
            str(new_status_raw)
        )
    
    old_status = old_status_raw  
    if isinstance(old_status_raw, dict):
        old_status = (
            old_status_raw.get("code") or
            old_status_raw.get("name") or
            str(old_status_raw)
        )
    
    # Применяем маппинг статусов для нормализации
    normalized_new_status = config.OKDESK_STATUS_MAPPING.get(new_status, new_status)
    normalized_old_status = config.OKDESK_STATUS_MAPPING.get(old_status, old_status) if old_status else None

    print(f"🔍 Извлечено: issue_id={issue_id}")
    print(f"🔍 Исходный статус: {new_status_raw} -> нормализованный: {normalized_new_status}")
    print(f"🔍 Предыдущий статус: {old_status_raw} -> нормализованный: {normalized_old_status}")
    print(f"🔍 OKDESK_STATUS_MAPPING: {config.OKDESK_STATUS_MAPPING}")
    print(f"🔍 RATING_REQUEST_STATUSES: {config.RATING_REQUEST_STATUSES}")

    if not issue_id or not new_status:
        print(f"❌ Недостаточно данных для изменения статуса: issue_id={issue_id}, new_status={new_status}")
        return

    print(f"📊 Изменение статуса заявки {issue_id}: {normalized_old_status or 'неизвестен'} -> {normalized_new_status}")

    # Находим заявку в нашей БД
    issue = IssueService.get_issue_by_okdesk_id(issue_id)
    if not issue:
        print(f"❌ Заявка {issue_id} не найдена в базе данных")
        return

    # Проверяем, действительно ли статус изменился
    status_actually_changed = normalized_new_status != issue.status
    new_status_is_completion = normalized_new_status.lower() in config.RATING_REQUEST_STATUSES or any(s in normalized_new_status.lower() for s in config.RATING_REQUEST_STATUSES)

    print(f"🔍 status_actually_changed: {status_actually_changed}")
    print(f"🔍 new_status_is_completion: {new_status_is_completion}")
    print(f"🔍 normalized_new_status: '{normalized_new_status}'")

    # Всегда обновляем статус в БД, даже если он "не изменился"
    # (могут приходить повторные webhook или статусы в разном порядке)
    updated_issue = IssueService.update_issue_status(issue.id, normalized_new_status)
    if updated_issue:
        print(f"✅ Статус заявки {issue_id} обновлен в БД: {issue.status} -> {normalized_new_status}")

        # Уведомляем пользователя ОБЯЗАТЕЛЬНО если:
        # 1. Статус действительно изменился, ИЛИ
        # 2. Новый статус является завершающим (проверка оценки будет внутри notify_user_status_change)
        should_notify = status_actually_changed or new_status_is_completion
        
        if should_notify:
            await notify_user_status_change(updated_issue, normalized_new_status, normalized_old_status)
            print(f"✅ Пользователь уведомлен об изменении статуса")
        else:
            print(f"ℹ️ Пропускаем уведомление: статус не изменился и не является завершающим")
    else:
        print(f"❌ Не удалось обновить статус заявки {issue_id} в БД")

    print(f"Status changed for issue {issue_id}: {normalized_old_status or 'unknown'} -> {normalized_new_status}")

async def notify_user_status_change(issue, new_status: str, old_status: str = None):
    """Уведомление пользователя о смене статуса"""
    from bot import bot  # Импортируем бота
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from database.crud import IssueService
    
    status_text = config.ISSUE_STATUS_MESSAGES.get(new_status, new_status)
    
    message = (
        f"📊 Статус заявки #{issue.issue_number} изменился\n\n"
        f"📝 {issue.title}\n\n"
        f"🔄 Новый статус: {status_text}"
    )
    
    # Создаем клавиатуру
    keyboard_buttons = []
    
    # Проверяем, нужно ли запрашивать оценку
    needs_rating = any(status in new_status.lower() for status in config.RATING_REQUEST_STATUSES) or new_status.lower() in config.RATING_REQUEST_STATUSES
    
    # НЕ отправляем запрос оценки, если заявка уже была оценена или запрос уже был отправлен
    if needs_rating and (issue.rating is not None or issue.rating_requested):
        if issue.rating is not None:
            print(f"⭐ ОЦЕНКА ПРОПУЩЕНА: заявка уже была оценена ({issue.rating}/5)")
        else:
            print(f"⭐ ОЦЕНКА ПРОПУЩЕНА: запрос оценки уже был отправлен")
        needs_rating = False
    
    print(f"⭐ Проверка необходимости оценки для статуса '{new_status}':")
    print(f"   📋 RATING_REQUEST_STATUSES: {config.RATING_REQUEST_STATUSES}")
    print(f"   🔍 new_status.lower(): '{new_status.lower()}'")
    print(f"   ⭐ issue.rating: {issue.rating}")
    print(f"   ✅ needs_rating: {needs_rating}")
    
    # Если статус изменился на статус, требующий оценки, добавляем запрос оценки качества
    if needs_rating:
        print(f"⭐ ДОБАВЛЯЕМ ЗАПРОС ОЦЕНКИ для статуса '{new_status}'")
        message += config.RATING_REQUEST_TEXT
        keyboard_buttons.extend([
            [InlineKeyboardButton(text="⭐⭐⭐⭐⭐ Отлично (5)", callback_data=f"rate_5_{issue.id}")],
            [InlineKeyboardButton(text="⭐⭐⭐⭐ Хорошо (4)", callback_data=f"rate_4_{issue.id}")],
            [InlineKeyboardButton(text="⭐⭐⭐ Нормально (3)", callback_data=f"rate_3_{issue.id}")],
            [InlineKeyboardButton(text="⭐⭐ Плохо (2)", callback_data=f"rate_2_{issue.id}")],
            [InlineKeyboardButton(text="⭐ Ужасно (1)", callback_data=f"rate_1_{issue.id}")]
        ])
    else:
        print(f"⭐ ОЦЕНКА НЕ ТРЕБУЕТСЯ для статуса '{new_status}'")
    
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
    sent_message = None
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
    
    # Если запрос оценки был добавлен и сообщение отправлено успешно, отмечаем что запрос был отправлен
    if needs_rating and (message_updated or sent_message):
        try:
            from models.database import SessionLocal
            db = SessionLocal()
            db_issue = db.query(Issue).filter(Issue.id == issue.id).first()
            if db_issue:
                db_issue.rating_requested = True
                db.commit()
                print(f"✅ Отмечено, что запрос оценки был отправлен для заявки {issue.id}")
        except Exception as e:
            print(f"⚠️ Не удалось обновить флаг rating_requested: {e}")
        finally:
            db.close()

async def notify_user_new_comment(issue, content: str, author: Dict):
    """Уведомление пользователя о новом комментарии"""
    from bot import bot  # Импортируем бота
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    # Правильно формируем имя автора
    author_name = "Неизвестен"
    if author:
        first_name = author.get("first_name", "")
        last_name = author.get("last_name", "")
        full_name = f"{first_name} {last_name}".strip()
        if full_name:
            author_name = full_name
        else:
            # Если нет first_name/last_name, пробуем поле name
            author_name = author.get("name", "Сотрудник")
    
    # Очищаем HTML-теги из контента
    clean_content = clean_html_content(content)
    
    # Ограничиваем длину комментария для Telegram
    max_comment_length = 150
    truncated_content = clean_content[:max_comment_length]
    if len(clean_content) > max_comment_length:
        truncated_content += "..."
    
    message = (
        f"💬 Новый комментарий к заявке #{issue.issue_number}\n\n"
        f"📝 {issue.title}\n"
        f"👤 От: {author_name}\n"
        f"💭 Комментарий:\n"
        f"┌─ {'─' * min(len(truncated_content), 30)} ─┐\n"
        f"│ {truncated_content} │\n"
        f"└─ {'─' * min(len(truncated_content), 30)} ─┘"
    )
    
    # Создаем клавиатуру с кнопками быстрого доступа
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Открыть в портале", url=issue.okdesk_url)],
        [InlineKeyboardButton(text="📝 Ответить", callback_data=f"add_comment_{issue.issue_number}")],
        [InlineKeyboardButton(text="📋 Мои заявки", callback_data="my_issues"),
         InlineKeyboardButton(text="📝 Создать заявку", callback_data="create_issue")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    print(f"📤 Отправка уведомления пользователю {issue.telegram_user_id} о комментарии к заявке #{issue.issue_number}")
    print(f"📝 Очищенный комментарий: {truncated_content[:50]}...")
    print(f"🔘 Кнопки: {[btn.text for row in keyboard.inline_keyboard for btn in row]}")
    
    try:
        sent_message = await bot.send_message(
            chat_id=issue.telegram_user_id,
            text=message,
            reply_markup=keyboard
        )
        print(f"✅ Уведомление о комментарии отправлено пользователю {issue.telegram_user_id}")
        print(f"📨 ID отправленного сообщения: {sent_message.message_id}")
        print(f"🔘 Клавиатура отправлена: {sent_message.reply_markup is not None}")
        if sent_message.reply_markup:
            print(f"🔘 Количество кнопок в клавиатуре: {len(sent_message.reply_markup.inline_keyboard)}")
    except Exception as e:
        print(f"❌ Failed to send comment notification: {e}")
        
        # Пробуем отправить упрощенное сообщение без клавиатуры
        try:
            simple_message = (
                f"💬 Новый комментарий к заявке #{issue.issue_number}\n\n"
                f"📝 {issue.title}\n"
                f"👤 От: {author_name}\n"
                f"💭 Комментарий: {truncated_content}\n\n"
                f"🔗 {issue.okdesk_url}"
            )
            
            await bot.send_message(
                chat_id=issue.telegram_user_id,
                text=simple_message
            )
            print(f"✅ Упрощенное уведомление о комментарии отправлено пользователю {issue.telegram_user_id}")
        except Exception as e2:
            print(f"❌ Даже упрощенное уведомление не удалось отправить: {e2}")
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

def clean_html_content(content: str) -> str:
    """Очистка HTML-тегов из контента для отправки в Telegram"""
    if not content:
        return ""
    
    # Заменяем блочные теги на пробелы, чтобы избежать склеивания слов
    content = re.sub(r'</(p|div|br|h[1-6]|li|ul|ol|blockquote)[^>]*>', ' ', content, flags=re.IGNORECASE)
    
    # Удаляем все остальные HTML-теги
    clean_text = re.sub(r'<[^>]+>', '', content)
    
    # Удаляем лишние пробелы и переносы строк
    clean_text = re.sub(r'\n\s*\n', '\n', clean_text)
    clean_text = re.sub(r'\s+', ' ', clean_text)
    
    # Удаляем специальные символы, которые могут вызвать проблемы
    clean_text = clean_text.replace('\r', '').replace('\t', ' ')
    
    return clean_text.strip()

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
