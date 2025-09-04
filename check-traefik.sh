#!/bin/bash

echo "🔍 Проверка конфигурации Traefik и n8n..."

# Проверяем сеть n8n
echo "📡 Доступные Docker сети:"
docker network ls | grep -E "(n8n|traefik)"

echo ""
echo "🏗️ Конфигурация n8n контейнеров:"
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}" | grep -E "(traefik|n8n)"

echo ""
echo "🔧 Проверяем метки Traefik в n8n:"
docker inspect n8n-traefik-1 --format='{{json .Config.Labels}}' | jq . 2>/dev/null || echo "jq не установлен, показываем raw:"
docker inspect n8n-traefik-1 --format='{{range $key, $value := .Config.Labels}}{{$key}}={{$value}}{{"\n"}}{{end}}' | grep traefik

echo ""
echo "🌐 Проверяем доступность домена:"
curl -I http://188.225.72.33/ 2>/dev/null || echo "Traefik не отвечает на HTTP"

echo ""
echo "✅ Анализ завершен!"
