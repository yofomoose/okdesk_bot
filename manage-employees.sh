#!/bin/bash

echo "👥 Управление сотрудниками Okdesk для правильного отображения авторов комментариев"

# Функция для добавления сотрудника
add_employee() {
    local name="$1"
    local email="$2"
    local position="$3"
    
    echo "➕ Добавление сотрудника: $name"
    
    # Формируем JSON данные
    cat > /tmp/employee_data.json << EOF
{
    "name": "$name",
    "email": "$email",
    "position": "$position",
    "active": true
}
EOF
    
    # Отправляем запрос к API
    curl -X POST "https://yapomogu55.okdesk.ru/api/v1/employees?api_token=4cf96e5bb33f06481e4aff5ff0a2aa740ce8490a" \
         -H "Content-Type: application/json" \
         -d @/tmp/employee_data.json
    
    echo ""
    rm -f /tmp/employee_data.json
}

# Функция для получения списка сотрудников
list_employees() {
    echo "📋 Список сотрудников в Okdesk:"
    curl -s "https://yapomogu55.okdesk.ru/api/v1/employees?api_token=4cf96e5bb33f06481e4aff5ff0a2aa740ce8490a" | \
        python3 -m json.tool 2>/dev/null || echo "Ошибка получения списка сотрудников"
    echo ""
}

# Функция для проверки пользователей бота
check_bot_users() {
    echo "🤖 Проверка пользователей бота, которые нуждаются в создании сотрудников..."
    
    # Получаем список пользователей из базы данных бота
    docker exec okdesk_bot_okdesk_bot_1 sqlite3 /app/data/okdesk_bot.db \
        "SELECT full_name, phone FROM users WHERE is_registered = 1 AND full_name IS NOT NULL;" 2>/dev/null | \
        while IFS='|' read -r name phone; do
            if [ -n "$name" ]; then
                echo "  • $name (тел: $phone)"
            fi
        done
    echo ""
}

# Основное меню
echo "Выберите действие:"
echo "1. Показать список сотрудников в Okdesk"
echo "2. Показать пользователей бота"
echo "3. Добавить сотрудника в Okdesk"
echo "4. Тестировать комментарий от имени пользователя"
echo "5. Выход"
echo ""

read -p "Введите номер действия: " choice

case $choice in
    1)
        list_employees
        ;;
    2)
        check_bot_users
        ;;
    3)
        read -p "Введите полное имя сотрудника: " emp_name
        read -p "Введите email сотрудника: " emp_email
        read -p "Введите должность сотрудника: " emp_position
        
        if [ -n "$emp_name" ] && [ -n "$emp_email" ]; then
            add_employee "$emp_name" "$emp_email" "$emp_position"
        else
            echo "❌ Имя и email обязательны"
        fi
        ;;
    4)
        echo "🧪 Тестирование комментария..."
        
        # Получаем ID первой открытой заявки
        issue_id=$(curl -s "https://yapomogu55.okdesk.ru/api/v1/issues?limit=1&api_token=4cf96e5bb33f06481e4aff5ff0a2aa740ce8490a" | \
                   python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0]['id'] if data else '')" 2>/dev/null)
        
        if [ -n "$issue_id" ]; then
            echo "📝 Создание тестового комментария к заявке #$issue_id..."
            
            # Создаем комментарий с указанием автора
            curl -X POST "https://yapomogu55.okdesk.ru/api/v1/issues/$issue_id/comments?api_token=4cf96e5bb33f06481e4aff5ff0a2aa740ce8490a" \
                 -H "Content-Type: application/json" \
                 -d '{
                     "content": "**От пользователя Telegram бота:**\n\nТестовый комментарий для проверки отображения автора",
                     "public": true
                 }'
            echo ""
        else
            echo "❌ Не найдено открытых заявок для тестирования"
        fi
        ;;
    5)
        echo "👋 До свидания!"
        exit 0
        ;;
    *)
        echo "❌ Неверный выбор"
        ;;
esac

echo ""
echo "💡 Полезная информация:"
echo "   • Для корректного отображения авторов комментариев нужно создать сотрудников в Okdesk"
echo "   • Имена сотрудников должны точно совпадать с именами пользователей бота"
echo "   • Если сотрудник не найден, имя будет добавлено в текст комментария"
echo "   • Проверить результат можно в веб-интерфейсе Okdesk"
echo ""
