# RSS News Poster Bot для Telegram-каналов 📡

Самый простой open-source бот, который автоматически постит новости из RSS в твой канал.

**Особенности:**
- Работает полностью в РФ (без VPN)
- Один клик через Docker
- Не дублирует посты
- Легко добавить свои ленты

## Запуск

```bash
cp .env.example .env
# отредактируй .env
docker-compose up -d --build
```

## Структура проекта

```
textrss-news-poster-bot/
├── bot.py           # Главный файл бота
├── config.py        # Конфигурация
├── rss_handler.py   # Обработка RSS лент
├── database.py      # База данных просмотренных постов
├── requirements.txt # Зависимости Python
├── .env.example     # Пример переменных окружения
├── Dockerfile       # Docker образ
└── docker-compose.yml # Docker Compose конфигурация
```

## Настройка

1. Скопируйте `.env.example` в `.env`
2. Отредактируйте `.env`:
   - `BOT_TOKEN` — токен вашего бота от @BotFather
   - `CHANNEL_ID` — ID канала (@yourchannel или -1001234567890)
   - `ADMIN_ID` — ваш Telegram ID
   - `CHECK_INTERVAL` — интервал проверки в секундах (по умолчанию 900 = 15 минут)

## Команды

- `/start` — запустить бота
- `/add <url>` — добавить RSS ленту

## Поддержка

⭐ Поставь звезду!
💰 Поддержать автора: Boosty / GitHub Sponsors
