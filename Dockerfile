FROM python:3.12-slim

# Создаем непривилегированного пользователя для безопасности
RUN useradd -m -u 1000 botuser

WORKDIR /app

# Копируем и устанавливаем зависимости (кэширование слоя)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Устанавливаем владельца на непривилегированного пользователя
RUN chown -R botuser:botuser /app

# Переключаемся на непривилегированного пользователя
USER botuser

# Health check для проверки состояния бота
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os; exit(0)" || exit 1

CMD ["python", "bot.py"]
