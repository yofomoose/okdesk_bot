# Документация по исправлению привязки контактов

## Обзор изменений

Мы внесли следующие улучшения в систему для решения проблемы привязки контактов к заявкам в Okdesk:

1. **Сохранение ID контактов в базе данных**
   - Добавлен автоматический поиск контактов по телефону с сохранением их ID
   - При создании новых контактов их ID теперь сохраняются в базе данных

2. **Сохранение ID компаний в базе данных**
   - Добавлен автоматический поиск компаний по ИНН с сохранением их ID
   - При создании заявки для клиентов с ИНН автоматически определяется компания

3. **Механизм обратного вызова (callback)**
   - Добавлена система передачи функций обратного вызова для асинхронного обновления информации

4. **Новые методы в сервисе пользователей**
   - `update_contact_id_by_telegram_id` - обновление ID контакта по Telegram ID
   - `update_company_id_by_telegram_id` - обновление ID компании по Telegram ID

5. **Исправление создания заявок**
   - Заявки теперь всегда правильно привязываются к контактам и компаниям

## Подробные изменения

### 1. Сохранение ID контактов при поиске

Метод `find_contact_by_phone` теперь автоматически сохраняет найденные ID контактов в базе данных:

```python
# В методе find_contact_by_phone
if response and isinstance(response, dict) and 'id' in response:
    # Поиск пользователя по телефону и обновление его okdesk_contact_id
    clean_search_phone = ''.join(c for c in phone if c.isdigit())
    users = db.execute("SELECT telegram_id, phone FROM users WHERE okdesk_contact_id IS NULL").fetchall()
    for user_id, user_phone in users:
        if user_phone:
            clean_user_phone = ''.join(c for c in user_phone if c.isdigit())
            # Сравниваем последние 10 цифр телефонов
            if clean_search_phone[-10:] == clean_user_phone[-10:]:
                db.execute(
                    "UPDATE users SET okdesk_contact_id = ? WHERE telegram_id = ?",
                    (response['id'], user_id)
                )
```

### 2. Поиск и сохранение компаний по ИНН

Добавлен новый метод `find_company_by_inn`, который находит компанию по ИНН и сохраняет её ID:

```python
async def find_company_by_inn(self, inn: str):
    # ...
    # Если найдена компания, обновим её ID для всех пользователей с этим ИНН
    users = db.execute(
        "SELECT telegram_id FROM users WHERE inn = ? AND okdesk_company_id IS NULL", 
        (clean_inn,)
    ).fetchall()
    
    for user_row in users:
        user_id = user_row[0]
        db.execute(
            "UPDATE users SET okdesk_company_id = ? WHERE telegram_id = ?",
            (company['id'], user_id)
        )
```

### 3. Механизм обратного вызова для обновления контактов

В методе `create_issue` добавлена поддержка функций обратного вызова:

```python
# Если контакт найден и предоставлена функция обратного вызова
if contact and 'id' in contact and 'update_contact_callback' in kwargs:
    await kwargs['update_contact_callback'](contact['id'])
```

В обработчике `handlers/issues.py`:

```python
# Определяем функцию обратного вызова
async def update_contact_callback(contact_id: int):
    await asyncio.get_event_loop().run_in_executor(
        None, 
        UserService.update_contact_id_by_telegram_id,
        user.telegram_id, 
        contact_id
    )
    
# Добавляем в параметры
user_data["update_contact_callback"] = update_contact_callback
```

### 4. Новые методы в сервисе пользователей

В `database/crud.py` добавлены методы:

```python
@staticmethod
def update_contact_id_by_telegram_id(telegram_id: int, contact_id: int) -> Optional[User]:
    """Обновить ID контакта OkDesk для пользователя по telegram_id"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            user.okdesk_contact_id = contact_id
            db.commit()
            db.refresh(user)
            return user
    finally:
        db.close()
```

### 5. Тестовые скрипты

Созданы тестовые скрипты для проверки функциональности:

- `test_contact_binding.py` - тестирование привязки контактов и компаний
- `reset_okdesk_ids.py` - сброс ID контактов и компаний в базе данных
- `sync_contacts_companies.py` - массовая синхронизация контактов и компаний
- `test_callback_workflow.py` - тестирование функций обратного вызова

## Как теперь работает система

1. При создании заявки система автоматически проверяет, есть ли у пользователя сохраненный ID контакта
2. Если нет, система пытается найти контакт по телефону через API Okdesk
3. Если контакт найден, его ID сохраняется в базе данных для будущего использования
4. Если контакт не найден, создается новый контакт и его ID сохраняется
5. Аналогичный процесс выполняется для компаний на основе ИНН
6. При создании комментариев система использует сохраненные ID для правильной привязки автора

## Тестирование изменений

Выполните следующие скрипты для тестирования:

1. Сбросить сохраненные ID:
```
python reset_okdesk_ids.py
```

2. Протестировать привязку контактов:
```
python test_contact_binding.py
```

3. Синхронизировать всех пользователей:
```
python sync_contacts_companies.py
```

4. Проверить работу функций обратного вызова:
```
python test_callback_workflow.py
```
