from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
import hmac
import hashlib
from database.crud import IssueService, CommentService, UserService
from services.okdesk_api import OkdeskAPI
import config

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
        event_data = data.get("data", data)
        
        print(f"📊 Event: {event}")
        
        try:
            if event == "issue.created":
                await handle_issue_created(event_data)
            elif event == "issue.updated":
                await handle_issue_updated(event_data)
            elif event == "comment.created":
                await handle_comment_created(event_data)
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
    issue_id = data.get("id")
    if not issue_id:
        return
    
    # Находим заявку в нашей БД
    issue = IssueService.get_issue_by_okdesk_id(issue_id)
    if not issue:
        print(f"Issue {issue_id} not found in database")
        return
    
    # Обновляем статус, если изменился
    new_status = data.get("status")
    if new_status and new_status != issue.status:
        IssueService.update_issue_status(issue.id, new_status)
        
        # Уведомляем пользователя о смене статуса
        await notify_user_status_change(issue, new_status)
    
    print(f"Issue {issue_id} updated")

async def handle_comment_created(data: Dict[str, Any]):
    """Обработка создания комментария"""
    print(f"🔍 Полные данные комментария: {json.dumps(data, indent=2, ensure_ascii=False)}")
    
    # Пробуем разные структуры данных
    # Вариант 1: issue и comment как отдельные объекты
    issue_data = data.get("issue", {})
    comment_data = data.get("comment", {})
    
    # Вариант 2: все данные в корне
    if not issue_data:
        issue_data = data.get("issue", data)
    if not comment_data:
        comment_data = data
    
    issue_id = issue_data.get("id")
    comment_id = comment_data.get("id")
    content = comment_data.get("content")
    author = comment_data.get("author", {})
    
    print(f"📝 Получен комментарий:")
    print(f"   🎫 Заявка ID: {issue_id}")
    print(f"   💬 Комментарий ID: {comment_id}")
    print(f"   📄 Содержимое: {content}")
    print(f"   👤 Автор: {author.get('name', 'Неизвестен')}")
    
    if not all([issue_id, comment_id, content]):
        print("❌ Недостаточно данных для обработки комментария")
        return
    
    # Находим заявку в нашей БД
    issue = IssueService.get_issue_by_okdesk_id(issue_id)
    if not issue:
        print(f"❌ Заявка {issue_id} не найдена в базе данных")
        return
    
    print(f"✅ Заявка найдена в БД: {issue.title}")
    
    # Проверяем, не наш ли это комментарий (чтобы избежать дублирования)
    existing_comment = CommentService.get_issue_comments(issue.id)
    for comment in existing_comment:
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
    
    # Уведомляем пользователя о новом комментарии
    await notify_user_new_comment(issue, content, author)
    print(f"✅ Пользователь уведомлен о новом комментарии")
    
    print(f"New comment from Okdesk: {comment_id}")

async def handle_status_changed(data: Dict[str, Any]):
    """Обработка смены статуса заявки"""
    issue_id = data.get("issue_id")
    new_status = data.get("new_status")
    old_status = data.get("old_status")
    
    if not all([issue_id, new_status]):
        return
    
    # Находим заявку в нашей БД
    issue = IssueService.get_issue_by_okdesk_id(issue_id)
    if not issue:
        print(f"Issue {issue_id} not found in database")
        return
    
    # Обновляем статус
    IssueService.update_issue_status(issue.id, new_status)
    
    # Уведомляем пользователя
    await notify_user_status_change(issue, new_status, old_status)
    
    print(f"Status changed for issue {issue_id}: {old_status} -> {new_status}")

async def notify_user_status_change(issue, new_status: str, old_status: str = None):
    """Уведомление пользователя о смене статуса"""
    from bot import bot  # Импортируем бота
    
    status_text = config.ISSUE_STATUS_MESSAGES.get(new_status, new_status)
    
    message = (
        f"📊 Статус заявки #{issue.issue_number} изменился\n\n"
        f"📝 {issue.title}\n"
        f"🔄 Новый статус: {status_text}"
    )
    
    if old_status:
        old_status_text = config.ISSUE_STATUS_MESSAGES.get(old_status, old_status)
        message += f"\n⬅️ Предыдущий статус: {old_status_text}"
    
    try:
        await bot.send_message(
            chat_id=issue.telegram_user_id,
            text=message
        )
    except Exception as e:
        print(f"Failed to send status notification: {e}")

async def notify_user_new_comment(issue, content: str, author: Dict):
    """Уведомление пользователя о новом комментарии"""
    from bot import bot  # Импортируем бота
    
    author_name = author.get("name", "Сотрудник")
    
    message = (
        f"💬 Новый комментарий к заявке #{issue.issue_number}\n\n"
        f"📝 {issue.title}\n"
        f"👤 От: {author_name}\n"
        f"💭 Комментарий: {content[:200]}{'...' if len(content) > 200 else ''}\n\n"
        f"🔗 Открыть заявку: {issue.okdesk_url}"
    )
    
    try:
        await bot.send_message(
            chat_id=issue.telegram_user_id,
            text=message
        )
    except Exception as e:
        print(f"Failed to send comment notification: {e}")

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
    
    # Информация о безопасности webhook
    if config.WEBHOOK_SECRET and config.WEBHOOK_SECRET.strip():
        print("🔐 Webhook защищен секретным ключом")
    else:
        print("⚠️  Webhook работает БЕЗ проверки подписи (не рекомендуется для продакшена)")
    
    print(f"🚀 Запуск webhook сервера на {config.HOST}:{config.PORT}")
    uvicorn.run(app, host=config.HOST, port=config.PORT)
