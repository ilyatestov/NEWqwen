from dotenv import load_dotenv
import os
import logging
from urllib.parse import urlparse
import ipaddress

load_dotenv()

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден в переменных окружения")
# Санитизация токена (убираем возможные пробелы)
BOT_TOKEN = BOT_TOKEN.strip()

CHANNEL_ID = os.getenv("CHANNEL_ID")
if not CHANNEL_ID:
    raise ValueError("❌ CHANNEL_ID не найден в переменных окружения")
CHANNEL_ID = CHANNEL_ID.strip()

ADMIN_ID = os.getenv("ADMIN_ID")
if not ADMIN_ID:
    raise ValueError("❌ ADMIN_ID не найден в переменных окружения")
try:
    ADMIN_ID = int(ADMIN_ID.strip())
except ValueError:
    raise ValueError("❌ ADMIN_ID должен быть числом")

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "900"))

# Пул соединений с БД
DB_PATH = os.getenv("DB_PATH", "seen_posts.db")

# Максимальное количество записей в БД (для очистки старых)
MAX_DB_ENTRIES = int(os.getenv("MAX_DB_ENTRIES", "10000"))

# Таймаут запросов к RSS (секунды)
RSS_TIMEOUT = int(os.getenv("RSS_TIMEOUT", "10"))

# Количество постов для проверки за один раз
POSTS_TO_CHECK = int(os.getenv("POSTS_TO_CHECK", "5"))

def is_valid_url(url: str) -> bool:
    """Проверяет, является ли URL валидным и не ведет на внутренний ресурс"""
    try:
        parsed = urlparse(url.strip())
        if parsed.scheme not in ["http", "https"]:
            return False
        if not parsed.netloc:
            return False
        # Проверка на внутренние IP-адреса (защита от SSRF)
        hostname = parsed.hostname
        if hostname:
            try:
                ip = ipaddress.ip_address(hostname)
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    logger.warning(f"Попытка доступа к внутреннему адресу: {hostname}")
                    return False
            except ValueError:
                # Это доменное имя, можно дополнительно проверить через DNS
                pass
        return True
    except Exception:
        return False

RSS_FEEDS = [
    # Добавляй свои ленты здесь или через команду /add
    "https://lenta.ru/rss",
    "https://habr.com/ru/rss/interesting/",
]
