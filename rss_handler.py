import feedparser
import logging
import asyncio
from aiogram import Bot
from database import is_seen, mark_seen, get_active_feeds
from config import RSS_FEEDS, POSTS_TO_CHECK, RSS_TIMEOUT, CHANNEL_ID, is_valid_url

logger = logging.getLogger(__name__)

# Разрешенные HTML теги для санитизации контента
ALLOWED_TAGS = {'b', 'strong', 'i', 'em', 'u', 'a', 'br', 'p'}

def sanitize_html(text: str) -> str:
    """Базовая санитизация HTML контента (удаляем опасные теги)"""
    if not text:
        return ""
    # Удаляем script, style и другие опасные теги
    dangerous_tags = ['script', 'style', 'iframe', 'object', 'embed', 'form']
    for tag in dangerous_tags:
        text = text.replace(f'<{tag}', '&lt;{tag}')
        text = text.replace(f'</{tag}', f'&lt;/{tag}&gt;')
    return text

async def fetch_feed(url: str) -> list:
    """Асинхронно парсит RSS ленту с таймаутом"""
    try:
        # Запускаем синхронный feedparser в executor чтобы не блокировать цикл событий
        loop = asyncio.get_event_loop()
        feed = await asyncio.wait_for(
            loop.run_in_executor(None, feedparser.parse, url),
            timeout=RSS_TIMEOUT
        )
        return feed.entries[:POSTS_TO_CHECK]
    except asyncio.TimeoutError:
        logger.warning(f"⏰ Таймаут при парсинге {url}")
        return []
    except Exception as e:
        logger.error(f"❌ Ошибка парсинга {url}: {e}")
        return []

async def check_and_post(bot: Bot):
    """Проверяет RSS ленты и публикует новые посты"""
    # Получаем активные ленты из БД или используем дефолтные
    feeds = await get_active_feeds()
    if not feeds:
        feeds = RSS_FEEDS
    
    logger.info(f"📡 Проверка {len(feeds)} RSS лент...")
    
    for url in feeds:
        # Валидация URL перед парсингом
        if not is_valid_url(url):
            logger.warning(f"⚠️ Неверный URL пропущен: {url}")
            continue
            
        entries = await fetch_feed(url)
        
        for entry in entries:
            link = entry.get('link', '')
            if not link:
                continue
                
            if await is_seen(link):
                continue
            
            # Формируем текст поста с санитизацией
            title = sanitize_html(entry.get('title', 'Без названия'))
            description = sanitize_html(entry.get('description', ''))
            
            # Обрезаем описание если слишком длинное
            if len(description) > 500:
                description = description[:500] + "..."
            
            post_text = f"📰 <b>{title}</b>\n\n{description}\n\n🔗 <a href='{link}'>Читать далее</a>"
            
            try:
                await bot.send_message(
                    CHANNEL_ID, 
                    post_text, 
                    parse_mode="HTML",
                    disable_web_page_preview=False
                )
                await mark_seen(link)
                logger.info(f"✅ Опубликован пост: {title[:50]}...")
            except Exception as e:
                logger.error(f"❌ Ошибка постинга: {e}")
                # Можно добавить retry-логику здесь
