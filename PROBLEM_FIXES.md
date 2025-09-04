# Руководство по исправлению проблем OKDesk Bot

## Проблемы и их решения

### 1. База данных создается заново при каждом запуске

**Проблема:** Webhook и bot используют разные файлы базы данных

**Решение:**
1. Исправлен fallback в `config.py`:
   ```python
   DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////app/data/okdesk_bot.db")
   ```

2. В `docker-compose.yml` оба контейнера используют одинаковую переменную окружения:
   ```yaml
   environment:
     - DATABASE_URL=sqlite:////app/data/okdesk_bot.db
   ```

3. Общий volume для данных:
   ```yaml
   volumes:
     - ./data:/app/data
   ```

### 2. Комментарии не приходят в Telegram

**Причины:**
- Webhook не находит заявку в базе данных (разные БД)
- Контакт не может быть создан из-за пустого last_name

**Решения:**
1. **Исправление базы данных** - см. пункт 1
2. **Исправление создания контактов** в `handlers/registration.py`:
   ```python
   last_name = name_parts[1] if len(name_parts) > 1 else "Клиент"
   ```

3. **Упрощенное добавление комментариев** в `services/okdesk_api.py`:
   ```python
   async def add_comment(self, issue_id: int, content: str, author_name: str = None):
       if author_name:
           formatted_content = f"**От клиента: {author_name}**\n\n{content}"
       else:
           formatted_content = content
       
       data = {
           'content': formatted_content,
           'public': True
       }
       # Не указываем author_id - используется владелец токена
   ```

### 3. Webhook показывает "0 заявок в БД"

**Причина:** Webhook и bot используют разные файлы базы данных

**Диагностика:**
```bash
# Linux/MacOS
make diagnose

# Windows PowerShell  
.\manage.ps1 diagnose

# Python диагностика
python full_diagnose.py
```

**Решение:** См. пункт 1 - исправление базы данных

### 4. Ошибка "last_name не может быть пустым"

**Причина:** API Okdesk требует заполненное поле last_name

**Решение:** Исправлено в `handlers/registration.py` - теперь используется "Клиент" как fallback

### 5. Комментарии показывают автора "Иван Киселев"

**Причина:** Использование фиксированного author_id системного пользователя

**Решение:** 
- Убран параметр author_id из запросов
- Имя клиента добавляется в текст комментария
- API автоматически использует владельца токена как автора

## Команды для управления

### Linux/MacOS:
```bash
make start          # Запуск всех сервисов
make stop           # Остановка сервисов  
make restart        # Перезапуск
make diagnose       # Полная диагностика
make logs           # Просмотр логов
make backup         # Резервное копирование
make update         # Обновление и перезапуск
```

### Windows PowerShell:
```powershell
.\manage.ps1 start      # Запуск всех сервисов
.\manage.ps1 stop       # Остановка сервисов
.\manage.ps1 restart    # Перезапуск  
.\manage.ps1 diagnose   # Полная диагностика
.\manage.ps1 logs       # Просмотр логов
.\manage.ps1 backup     # Резервное копирование
.\manage.ps1 update     # Обновление и перезапуск
```

## Проверка исправлений

1. **Остановите контейнеры:**
   ```bash
   make stop
   # или
   .\manage.ps1 stop
   ```

2. **Перезапустите с новой конфигурацией:**
   ```bash
   make start
   # или
   .\manage.ps1 start
   ```

3. **Проверьте диагностику:**
   ```bash
   make diagnose
   # или  
   .\manage.ps1 diagnose
   ```

4. **Создайте тестовую заявку через бота**

5. **Добавьте комментарий через Okdesk веб-интерфейс**

6. **Проверьте, что уведомление пришло в Telegram**

## Логи для отладки

```bash
# Показать логи webhook
docker-compose logs -f webhook

# Показать логи бота
docker-compose logs -f bot

# Показать все логи
make logs
```

## Если проблемы остались

1. Проверьте, что в `data/okdesk_bot.db` действительно есть заявки:
   ```bash
   python full_diagnose.py
   ```

2. Убедитесь, что webhook получает события:
   ```bash
   docker-compose logs webhook | grep "comment"
   ```

3. Проверьте настройки webhook в Okdesk (URL должен быть доступен извне)

4. Убедитесь, что токен API имеет необходимые права для создания контактов и комментариев
