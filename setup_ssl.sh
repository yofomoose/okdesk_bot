#!/bin/bash
# Скрипт для настройки SSL сертификата с Let's Encrypt

echo "🔐 Настройка SSL сертификата для okbot.teftelyatun.ru"

# Установка certbot
sudo apt-get update
sudo apt-get install -y certbot

# Временно останавливаем Docker контейнеры
docker-compose down

# Получаем сертификат
sudo certbot certonly --standalone \
  --preferred-challenges http \
  -d okbot.teftelyatun.ru \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email

# Создаем директорию для сертификатов
mkdir -p ./ssl

# Копируем сертификаты
sudo cp /etc/letsencrypt/live/okbot.teftelyatun.ru/fullchain.pem ./ssl/
sudo cp /etc/letsencrypt/live/okbot.teftelyatun.ru/privkey.pem ./ssl/
sudo chown $USER:$USER ./ssl/*.pem

# Обновляем docker-compose.yml для HTTPS
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  okdesk_bot:
    build: .
    container_name: okdesk_bot
    volumes:
      - ./data:/app/data
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - OKDESK_API_URL=${OKDESK_API_URL}
      - OKDESK_API_TOKEN=${OKDESK_API_TOKEN}
      - DATABASE_URL=sqlite:///data/okdesk_bot.db
      - ADMIN_IDS=${ADMIN_IDS}
    depends_on:
      - okdesk_webhook
    restart: unless-stopped

  okdesk_webhook:
    build: .
    command: python webhook_server.py
    container_name: okdesk_webhook
    ports:
      - "80:8000"
      - "443:8443"
    volumes:
      - ./data:/app/data
      - ./ssl:/app/ssl:ro
    environment:
      - OKDESK_API_URL=${OKDESK_API_URL}
      - OKDESK_API_TOKEN=${OKDESK_API_TOKEN}
      - DATABASE_URL=sqlite:///data/okdesk_bot.db
      - WEBHOOK_SECRET=${WEBHOOK_SECRET}
      - SSL_CERT_PATH=/app/ssl/fullchain.pem
      - SSL_KEY_PATH=/app/ssl/privkey.pem
    restart: unless-stopped

volumes:
  data:
    driver: local
EOF

echo "✅ SSL настроен. Обновите .env файл на HTTPS URL"
echo "WEBHOOK_URL=https://okbot.teftelyatun.ru/okdesk-webhook"
