# Настройка Nginx Proxy Manager для OKDesk Bot

## Обзор архитектуры

```
Интернет → NPM (порты 80/443) → OKDesk Webhook (порт 8000) → Telegram Bot
          ↓
     SSL сертификат Let's Encrypt
```

## Шаг 1: Развертывание с NPM

### На сервере Linux:
```bash
# Скопируйте файлы на сервер
scp docker-compose.with-npm.yml user@server:/opt/okdesk_bot/
scp deploy-with-npm.sh user@server:/opt/okdesk_bot/

# Запустите развертывание
chmod +x deploy-with-npm.sh
./deploy-with-npm.sh
```

### На Windows (локально для тестирования):
```powershell
.\deploy-with-npm.ps1
```

## Шаг 2: Настройка NPM

### 1. Откройте Admin Panel
- URL: `http://188.225.72.33:81`
- Email: `admin@example.com`
- Password: `changeme`

### 2. Смените пароль
- После входа обязательно смените пароль
- Обновите email на ваш

### 3. Добавьте Proxy Host

#### Перейдите в "Proxy Hosts" → "Add Proxy Host"

**Tab "Details":**
- Domain Name: `okbot.teftelyatun.ru`
- Scheme: `http`
- Forward Hostname/IP: `okdesk_webhook`
- Forward Port: `8000`
- ✅ Cache Assets
- ✅ Block Common Exploits
- ✅ Websockets Support

**Tab "SSL":**
- ✅ SSL Certificate
- Выберите "Request a new SSL Certificate"
- ✅ Force SSL
- ✅ HTTP/2 Support
- ✅ HSTS Enabled
- Email: ваш email для Let's Encrypt
- ✅ I Agree to the Let's Encrypt Terms of Service

### 4. Сохраните настройки

## Шаг 3: Обновление DNS

Убедитесь, что DNS запись для `okbot.teftelyatun.ru` указывает на `188.225.72.33`

## Шаг 4: Тестирование

### Проверка SSL:
```bash
curl -I https://okbot.teftelyatun.ru/health
```

### Ожидаемый ответ:
```
HTTP/2 200
server: nginx
content-type: application/json
```

## Шаг 5: Обновление Okdesk Webhook

В панели Okdesk обновите URL webhook на:
`https://okbot.teftelyatun.ru/okdesk-webhook`

## Преимущества NPM

✅ **Автоматический SSL** - Let's Encrypt сертификаты обновляются автоматически
✅ **Централизованное управление** - один интерфейс для всех доменов
✅ **Безопасность** - блокировка атак, rate limiting
✅ **Мониторинг** - логи и статистика
✅ **Высокая доступность** - nginx как reverse proxy

## Troubleshooting

### Проблема: NPM не может получить сертификат
**Решение:** Убедитесь что:
- DNS корректно настроен
- Порт 80 открыт для HTTP validation
- Домен доступен из интернета

### Проблема: 502 Bad Gateway
**Решение:** Проверьте:
- Контейнер webhook запущен: `docker-compose -f docker-compose.with-npm.yml ps`
- Логи webhook: `docker-compose -f docker-compose.with-npm.yml logs okdesk_webhook`

### Проблема: SSL сертификат не создается
**Решение:**
- Проверьте что домен резолвится в правильный IP
- Убедитесь что Cloudflare отключен (серое облачко) во время создания сертификата
- После создания сертификата можно включить Cloudflare обратно

## Команды для управления

```bash
# Просмотр логов NPM
docker-compose -f docker-compose.with-npm.yml logs nginx-proxy-manager

# Просмотр логов webhook
docker-compose -f docker-compose.with-npm.yml logs okdesk_webhook

# Перезапуск всех сервисов
docker-compose -f docker-compose.with-npm.yml restart

# Обновление контейнеров
docker-compose -f docker-compose.with-npm.yml pull
docker-compose -f docker-compose.with-npm.yml up -d
```
