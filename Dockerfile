# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем метаданные
LABEL maintainer="okdesk_bot"
LABEL version="1.0"
LABEL description="Okdesk Telegram Bot"

# Устанавливаем переменные окружения для Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Копируем только файлы зависимостей для кэширования
COPY requirements.txt ./

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Копируем только необходимые файлы приложения
COPY bot.py webhook_server.py config.py ./
COPY handlers/ ./handlers/
COPY services/ ./services/
COPY models/ ./models/
COPY database/ ./database/
COPY utils/ ./utils/

# Создаем директорию для базы данных
RUN mkdir -p /app/data /app/logs

# Создаем пользователя с ограниченными правами
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Добавляем health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Открываем порт
EXPOSE 8000

# Команда по умолчанию
CMD ["python", "bot.py"]
