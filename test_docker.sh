#!/bin/bash
# Скрипт для тестирования webhook изнутри Docker контейнера

echo "🔍 Проверяем статус контейнеров..."
docker compose ps

echo -e "\n📊 Проверяем порты..."
netstat -tulpn | grep :8000 || echo "Порт 8000 не слушается"

echo -e "\n🏥 Тестируем webhook изнутри Docker сети..."
docker compose exec okdesk_webhook curl -s http://localhost:8000/health || echo "Health endpoint недоступен"

echo -e "\n📡 Тестируем webhook endpoint изнутри Docker сети..."
docker compose exec okdesk_webhook curl -s -X POST http://localhost:8000/okdesk-webhook \
  -H "Content-Type: application/json" \
  -d '{"event":"comment_created","data":{"comment":{"id":999,"content":"тест","author":{"id":1,"name":"тест"},"issue":{"id":81,"title":"тест"}}}}' || echo "Webhook endpoint недоступен"

echo -e "\n🌐 Тестируем внешний доступ к серверу..."
curl -s -m 5 http://localhost:8000/health || echo "Внешний доступ недоступен"

echo -e "\n📋 Последние логи webhook сервера..."
docker compose logs okdesk_webhook --tail=10
