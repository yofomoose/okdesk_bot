# Интеграция с существующим Traefik

## Проблема
У вас уже запущен Traefik от n8n, который занимает порты 80 и 443. NPM не может запуститься из-за конфликта портов.

## Решение: Использование существующего Traefik

### Шаг 1: Проверка конфигурации Traefik

Выполните на сервере:
```bash
cd /opt/okdesk_bot
git pull
chmod +x check-traefik.sh
./check-traefik.sh
```

### Шаг 2: Интеграция с Traefik

```bash
chmod +x setup-traefik.sh
./setup-traefik.sh
```

### Шаг 3: Проверка результата

Через 1-2 минуты после запуска:
```bash
# Проверка доступности
curl -I https://okbot.teftelyatun.ru/health

# Ожидаемый результат:
# HTTP/2 200 
# server: nginx/1.x.x
# content-type: application/json
```

## Как это работает

### 1. Docker Labels
В `docker-compose.traefik.yml` добавлены метки:
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.okdesk-webhook.rule=Host(`okbot.teftelyatun.ru`)"
  - "traefik.http.routers.okdesk-webhook.tls=true"
  - "traefik.http.routers.okdesk-webhook.tls.certresolver=letsencrypt"
```

### 2. Сетевая интеграция
Webhook контейнер подключается к сети n8n:
```yaml
networks:
  - n8n_default  # Сеть от существующего Traefik
```

### 3. Автоматический SSL
Traefik автоматически:
- Создает SSL сертификат через Let's Encrypt
- Настраивает редирект HTTP → HTTPS
- Обновляет сертификаты

## Troubleshooting

### Проблема: Сеть n8n_default не найдена
```bash
# Проверяем доступные сети
docker network ls

# Если сеть называется по-другому, обновите docker-compose.traefik.yml
# Замените "n8n_default" на правильное имя
```

### Проблема: 404 Not Found
```bash
# Проверяем метки контейнера
docker inspect okdesk_bot_okdesk_webhook_1 --format='{{range $key, $value := .Config.Labels}}{{$key}}={{$value}}{{"\n"}}{{end}}' | grep traefik

# Перезапускаем Traefik для обновления конфигурации
docker restart n8n-traefik-1
```

### Проблема: SSL сертификат не создается
```bash
# Проверяем DNS
nslookup okbot.teftelyatun.ru

# Должен возвращать: 188.225.72.33

# Проверяем логи Traefik
docker logs n8n-traefik-1 -f
```

## Альтернативное решение: NPM на других портах

Если Traefik интеграция не работает:

```bash
./fix-npm-ports.sh
```

Тогда webhook URL будет: `https://188.225.72.33:8443/okdesk-webhook`

## Проверка работы webhook

```bash
# Тест доступности
curl -X POST https://okbot.teftelyatun.ru/okdesk-webhook \
  -H "Content-Type: application/json" \
  -d '{"event": "test", "data": {"message": "test"}}'

# Ожидаемый ответ:
# {"detail": "Missing required fields: event and data"}
# Это нормально - означает что endpoint доступен
```

## Обновление webhook в Okdesk

После успешной настройки обновите в панели Okdesk:
- Webhook URL: `https://okbot.teftelyatun.ru/okdesk-webhook`
- События: Комментарии к заявкам

## Мониторинг

```bash
# Логи webhook
docker-compose -f docker-compose.traefik.yml logs okdesk_webhook -f

# Логи Traefik
docker logs n8n-traefik-1 -f | grep okbot
```
