# Диагностика проблем с webhook сервером

## Проблема
- Cloudflare возвращает 404 для okbot.teftelyatun.ru
- Прямой доступ к IP 92.124.128.162:8000 возвращает 502
- Docker контейнеры запущены согласно логам, но недоступны извне

## Команды для диагностики на сервере

### 1. Проверить статус Docker контейнеров
```bash
docker compose ps
docker compose logs --tail=20
```

### 2. Проверить, какие порты слушает сервер
```bash
netstat -tulpn | grep :8000
ss -tulpn | grep :8000
```

### 3. Проверить доступность изнутри сервера
```bash
curl http://localhost:8000/health
curl http://127.0.0.1:8000/health
curl http://0.0.0.0:8000/health
```

### 4. Проверить Docker сеть
```bash
docker network ls
docker compose exec okdesk_webhook curl http://localhost:8000/health
```

### 5. Проверить firewall
```bash
ufw status
iptables -L
```

### 6. Проверить логи системы
```bash
journalctl -u docker --tail=20
dmesg | tail
```

## Возможные решения

### Решение 1: Перезапуск с принудительной пересборкой
```bash
docker compose down
docker compose up -d --build --force-recreate
```

### Решение 2: Проверка конфигурации хоста
Убедиться, что в docker-compose.yml webhook сервис использует:
```yaml
ports:
  - "8000:8000"
```

### Решение 3: Проверка .env файла
Убедиться, что HOST=0.0.0.0 в .env файле

### Решение 4: Проверка Cloudflare настроек
- Убедиться, что проксирование включено (оранжевое облако)
- Проверить правила переадресации
- Возможно нужно настроить SSL режим на "Flexible"

## Тестирование после исправления
```bash
# На сервере
curl http://localhost:8000/health

# Извне
curl https://okbot.teftelyatun.ru/health
```
