import aiosqlite
import hashlib
import logging
from config import DB_PATH, MAX_DB_ENTRIES

logger = logging.getLogger(__name__)

# Пул соединений (глобальная переменная для переиспользования)
_db_pool = None

async def get_db_connection():
    """Получает соединение из пула или создает новое"""
    global _db_pool
    if _db_pool is None:
        # Включаем WAL режим для лучшей производительности
        _db_pool = await aiosqlite.connect(DB_PATH)
        await _db_pool.execute("PRAGMA journal_mode=WAL")
        await _db_pool.execute("PRAGMA synchronous=NORMAL")
        await _db_pool.commit()
    return _db_pool

async def init_db():
    """Инициализирует БД и создает индекс"""
    db = await get_db_connection()
    await db.execute("""
        CREATE TABLE IF NOT EXISTS seen (
            hash TEXT PRIMARY KEY,
            link TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Добавляем индекс для ускорения поиска
    await db.execute("CREATE INDEX IF NOT EXISTS idx_hash ON seen(hash)")
    await db.commit()
    logger.info("✅ База данных инициализирована")

async def is_seen(link: str) -> bool:
    """Проверяет, была ли ссылка уже обработана (используем SHA-256)"""
    h = hashlib.sha256(link.encode()).hexdigest()
    db = await get_db_connection()
    async with db.execute("SELECT 1 FROM seen WHERE hash=?", (h,)) as cursor:
        return await cursor.fetchone() is not None

async def mark_seen(link: str):
    """Отмечает ссылку как просмотренную"""
    h = hashlib.sha256(link.encode()).hexdigest()
    db = await get_db_connection()
    try:
        await db.execute("INSERT OR IGNORE INTO seen (hash, link) VALUES (?, ?)", (h, link))
        await db.commit()
        # Периодическая очистка старых записей
        await cleanup_old_entries()
    except Exception as e:
        logger.error(f"Ошибка при сохранении в БД: {e}")

async def cleanup_old_entries():
    """Удаляет старые записи, если их слишком много"""
    db = await get_db_connection()
    # Получаем количество записей
    async with db.execute("SELECT COUNT(*) FROM seen") as cursor:
        count = (await cursor.fetchone())[0]
    
    if count > MAX_DB_ENTRIES:
        # Удаляем самые старые записи, оставляя только MAX_DB_ENTRIES
        await db.execute(f"""
            DELETE FROM seen 
            WHERE hash IN (
                SELECT hash FROM seen 
                ORDER BY created_at ASC 
                LIMIT {count - MAX_DB_ENTRIES}
            )
        """)
        await db.commit()
        logger.info(f"🧹 Удалено {count - MAX_DB_ENTRIES} старых записей из БД")

async def add_feed_to_db(url: str) -> bool:
    """Добавляет RSS ленту в БД"""
    db = await get_db_connection()
    try:
        await db.execute(
            "INSERT OR IGNORE INTO feeds (url, active) VALUES (?, ?)", 
            (url, True)
        )
        await db.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка при добавлении ленты: {e}")
        return False

async def get_active_feeds() -> list:
    """Получает список активных RSS лент из БД"""
    db = await get_db_connection()
    # Создаем таблицу feeds если нет
    await db.execute("""
        CREATE TABLE IF NOT EXISTS feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await db.commit()
    
    async with db.execute("SELECT url FROM feeds WHERE active = TRUE") as cursor:
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

async def remove_feed_from_db(url: str) -> bool:
    """Деактивирует RSS ленту в БД"""
    db = await get_db_connection()
    try:
        await db.execute("UPDATE feeds SET active = FALSE WHERE url = ?", (url,))
        await db.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка при удалении ленты: {e}")
        return False

async def get_stats() -> dict:
    """Возвращает статистику по БД"""
    db = await get_db_connection()
    async with db.execute("SELECT COUNT(*) FROM seen") as cursor:
        seen_count = (await cursor.fetchone())[0]
    async with db.execute("SELECT COUNT(*) FROM feeds WHERE active = TRUE") as cursor:
        feeds_count = (await cursor.fetchone())[0]
    return {"seen_posts": seen_count, "active_feeds": feeds_count}
