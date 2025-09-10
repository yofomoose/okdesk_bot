#!/bin/bash

# Скрипт для запуска тестов проверки исправлений в боте Okdesk
# Автоматически создает виртуальное окружение, устанавливает зависимости и запускает тесты

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Функция для проверки успешности выполнения команды
check_exit_code() {
    if [ $? -ne 0 ]; then
        echo -e "${RED}Произошла ошибка при выполнении предыдущей команды${NC}"
        exit 1
    fi
}

# Функция для вывода заголовков
print_header() {
    echo -e "\n${CYAN}============================================"
    echo " $1"
    echo "============================================${NC}"
}

print_header "Запуск проверки исправлений бота Okdesk"

# Проверяем, установлен ли Python
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}Python не установлен. Пожалуйста, установите Python 3.7+${NC}"
    exit 1
fi

# Выводим версию Python
PYTHON_VERSION=$($PYTHON_CMD --version)
echo -e "${GREEN}Найден $PYTHON_VERSION${NC}"

# Проверяем, установлен ли pip
$PYTHON_CMD -m pip --version > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo -e "${RED}pip не установлен. Пожалуйста, установите pip для Python${NC}"
    exit 1
fi

# Создаем виртуальное окружение, если его нет
if [ ! -d "venv" ]; then
    print_header "Создание виртуального окружения"
    $PYTHON_CMD -m venv venv
    check_exit_code
    echo -e "${GREEN}Виртуальное окружение создано${NC}"
else
    echo -e "${GREEN}Виртуальное окружение уже существует${NC}"
fi

# Активируем виртуальное окружение
echo -e "${YELLOW}Активация виртуального окружения...${NC}"
source venv/bin/activate
check_exit_code
echo -e "${GREEN}Виртуальное окружение активировано${NC}"

# Устанавливаем зависимости
print_header "Установка зависимостей"
pip install -r requirements.txt
check_exit_code
echo -e "${GREEN}Зависимости установлены${NC}"

# Предлагаем варианты запуска тестов
print_header "Выберите режим проверки"
echo -e "${YELLOW}1. Быстрая проверка (рекомендуется)${NC}"
echo -e "${YELLOW}2. Полный набор тестов${NC}"
echo -e "${YELLOW}3. Только диагностические инструменты${NC}"
echo -e "${YELLOW}4. Полный набор тестов с подробным выводом${NC}"
echo -e "${YELLOW}5. Выход${NC}"

read -p "Выберите опцию (1-5): " choice

case $choice in
    1)
        print_header "Запуск быстрой проверки"
        python quick_check_fixes.py
        ;;
    2)
        print_header "Запуск полного набора тестов"
        python run_all_tests.py
        ;;
    3)
        print_header "Запуск диагностических инструментов"
        python run_all_tests.py --diagnostic
        ;;
    4)
        print_header "Запуск полного набора тестов с подробным выводом"
        python run_all_tests.py --all --verbose
        ;;
    5)
        echo -e "${YELLOW}Выход${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}Неверный выбор${NC}"
        exit 1
        ;;
esac

# Проверяем результат выполнения
if [ $? -eq 0 ]; then
    print_header "ПРОВЕРКА ЗАВЕРШЕНА УСПЕШНО"
    echo -e "${GREEN}Все тесты пройдены успешно!${NC}"
    echo -e "${GREEN}Исправления работают корректно.${NC}"
else
    print_header "ПРОВЕРКА ЗАВЕРШЕНА С ОШИБКАМИ"
    echo -e "${RED}Некоторые тесты не пройдены.${NC}"
    echo -e "${YELLOW}Пожалуйста, проверьте результаты выше или запустите тесты с опцией --verbose для получения подробной информации.${NC}"
fi

# Деактивируем виртуальное окружение
deactivate

read -p "Нажмите Enter для выхода"
