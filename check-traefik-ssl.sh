#!/bin/bash

echo "🔧 Настройка Traefik с Let's Encrypt SSL..."

# Проверяем существующую конфигурацию Traefik
echo "📋 Проверка текущей конфигурации Traefik..."

N8N_DIR=$(docker inspect n8n-traefik-1 --format='{{range .Mounts}}{{if eq .Destination "/etc/traefik"}}{{.Source}}{{end}}{{end}}' 2>/dev/null)

if [ -n "$N8N_DIR" ]; then
    echo "📁 Найдена директория конфигурации: $N8N_DIR"
    echo "📄 Содержимое:"
    ls -la "$N8N_DIR" 2>/dev/null || echo "Нет доступа к директории"
else
    echo "❓ Директория конфигурации не найдена"
fi

echo ""
echo "🔍 Переменные окружения Traefik:"
docker inspect n8n-traefik-1 --format='{{range .Config.Env}}{{println .}}{{end}}' | grep -i -E "(TRAEFIK|ACME|CERT|SSL)"

echo ""
echo "🔍 Аргументы командной строки:"
docker inspect n8n-traefik-1 --format='{{.Config.Cmd}}'

echo ""
echo "📋 Для настройки SSL нужно:"
echo "   1. Добавить certificate resolver в конфигурацию Traefik"
echo "   2. Или использовать аргументы командной строки"
echo ""
echo "🔧 Возможные решения:"
echo "   A) Обновить конфигурацию n8n Traefik"
echo "   B) Создать отдельный Traefik с SSL"
echo ""
