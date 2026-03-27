# 🛡️ RSS Sentinel

**Advanced RSS Feed Management Platform with Intelligent Filtering & Multi-Platform Publishing**

RSS Sentinel — это мощная платформа для управления RSS-лентами с продвинутой фильтрацией контента, защитой от дубликатов и публикацией в различные социальные сети через удобный веб-интерфейс и Telegram-бота.

## ✨ Возможности

### 🔒 Безопасность
- **SSRF Protection** — валидация URL и блокировка внутренних IP-адресов
- **XSS Prevention** — санитизация HTML с белым списком тегов
- **Валидация токенов** — проверка формата BOT_TOKEN
- **SQL Injection защита** — параметризованные запросы
- **Non-root Docker** — запуск от непривилегированного пользователя

### 🎯 Умная фильтрация
- **Дедупликация** — SHA-256 хеширование для предотвращения повторов
- **Ключевые слова** — белые и черные списки для точной фильтрации
- **Минимальная длина** — отсев коротких/бессодержательных постов
- **Релевантность** — оценка важности контента по ключевым словам
- **Regex фильтры** — сложные правила фильтрации

### 📸 Медиа поддержка
- **Автозагрузка картинок** — извлечение и кэширование изображений
- **Мульти-платформенность** — адаптация под Telegram, VK, Twitter
- **Шаблоны постов** — настраиваемый формат публикаций

### 📊 Аналитика
- **Статистика** — общий обзор и по каждой ленте
- **Графики** — активность за 7 дней
- **Логи** — аудит всех действий системы

### 🌐 Веб-интерфейс
- **Dashboard** — управление лентами в реальном времени
- **Filter Preview** — тестирование фильтров перед применением
- **Адаптивный дизайн** — работает на любых устройствах
- **Темная тема** — приятный интерфейс для работы

## 📁 Структура проекта

```
rss-sentinel/
├── backend/app/
│   ├── api/              # REST API endpoints
│   ├── core/             # Конфигурация и валидация
│   ├── db/               # База данных (session, models)
│   ├── services/         # Бизнес-логика (feeds, parser)
│   ├── filters/          # Движок фильтрации
│   └── main.py           # FastAPI приложение
├── frontend/dist/        # Vue.js Dashboard (SPA)
├── docker/
│   └── Dockerfile        # Production образ
├── docker-compose.yml    # Оркестрация контейнеров
├── .env.example          # Шаблон конфигурации
└── README.md             # Документация
```

## 🚀 Быстрый старт

### Шаг 1: Подготовка

Установите **Docker** и **Docker Compose**:
```bash
# Проверка установки
docker --version
docker-compose --version
```

### Шаг 2: Клонирование и настройка

```bash
# Перейдите в директорию проекта
cd rss-sentinel

# Скопируйте шаблон конфигурации
cp .env.example .env

# Отредактируйте .env файл
nano .env
```

**Обязательные параметры:**
- `BOT_TOKEN` — токен от @BotFather в Telegram
- `ADMIN_IDS` — ваши Telegram ID (можно узнать через @userinfobot)

**Пример .env:**
```env
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_IDS=123456789,987654321
SECRET_KEY=my-super-secret-key-change-this
WEB_PORT=8000
```

### Шаг 3: Запуск

```bash
# Сборка и запуск контейнера
docker-compose up -d --build

# Проверка статуса
docker-compose ps

# Просмотр логов
docker-compose logs -f
```

### Шаг 4: Доступ

- **Веб-интерфейс**: http://localhost:8000/dashboard
- **API Документация**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📖 Использование

### Добавление RSS-ленты через Web UI

1. Откройте http://localhost:8000/dashboard
2. Перейдите на вкладку **"➕ Add Feed"**
3. Заполните поля:
   - **RSS URL** — ссылка на RSS-ленту
   - **Title** — название (опционально)
   - **Check Interval** — интервал проверки (секунды)
   - **Include Keywords** — ключевые слова для включения (через запятую)
   - **Exclude Keywords** — ключевые слова для исключения
   - **Min Content Length** — минимальная длина контента
   - **Post Template** — шаблон поста ({title}, {content}, {link})
4. Нажмите **"➕ Add Feed"**

### Тестирование фильтров

1. Перейдите на вкладку **"🔍 Filter Preview"**
2. Введите тестовые данные (заголовок, контент, ссылку)
3. Укажите параметры фильтрации
4. Нажмите **"🧪 Test Filter"**
5. Система покажет, будет ли контент опубликован или отфильтрован

### Управление лентами

- **⏯️ Toggle** — включить/выключить ленту
- **✏️ Edit** — редактировать настройки
- **🗑️ Delete** — удалить ленту

### API Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/feeds` | Список всех лент |
| POST | `/api/feeds?url=...` | Добавить ленту |
| DELETE | `/api/feeds/{id}` | Удалить ленту |
| PUT | `/api/feeds/{id}/toggle` | Включить/выключить |
| PUT | `/api/feeds/{id}` | Обновить настройки |
| POST | `/api/feeds/{id}/check` | Проверить сейчас |
| GET | `/api/stats` | Общая статистика |
| GET | `/api/stats/{id}` | Статистика ленты |
| POST | `/api/filter/preview` | Тест фильтра |

## ⚙️ Настройка фильтров

### Примеры конфигурации

**Только AI новости:**
```
Include: artificial intelligence, machine learning, neural networks
Exclude: advertisement, spam, clickbait
Min Length: 100
```

**Технологии без криптовалют:**
```
Include: tech, software, programming
Exclude: crypto, bitcoin, nft, casino
Min Length: 50
```

**Шаблон поста для Telegram:**
```
📰 {title}

{content}

🔗 Читать далее: {link}

#tech #news
```

## 🔧 Обслуживание

### Просмотр логов
```bash
docker-compose logs -f rss-sentinel
```

### Остановка
```bash
docker-compose down
```

### Перезапуск
```bash
docker-compose restart
```

### Обновление
```bash
git pull
docker-compose down
docker-compose up -d --build
```

### Резервное копирование БД
```bash
# Данные хранятся в ./data/sentinel.db
cp ./data/sentinel.db ./backup/sentinel_$(date +%Y%m%d).db
```

## 🛠 Технологии

- **Backend**: FastAPI, SQLAlchemy, Pydantic
- **Frontend**: Vue.js 3, Chart.js
- **Database**: SQLite (WAL mode)
- **Parser**: feedparser, BeautifulSoup4
- **Scheduler**: APScheduler
- **Container**: Docker, Docker Compose

## 📝 Лицензия

MIT License

## 🤝 Поддержка

При возникновении проблем:
1. Проверьте логи: `docker-compose logs`
2. Убедитесь, что `.env` настроен правильно
3. Проверьте доступность RSS-лент
4. Убедитесь, что порт 8000 свободен

## 🎯 Планы развития

- [ ] Поддержка Telegram Web Apps
- [ ] Интеграция с VK/Twitter API
- [ ] Система плагинов
- [ ] Мультипользовательский режим
- [ ] Экспорт/импорт конфигурации
- [ ] Email уведомления
- [ ] Discord интеграция

---

**RSS Sentinel** — ваш надежный помощник в мире RSS-агрегации! 🚀
