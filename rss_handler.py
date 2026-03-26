import feedparser
from aiogram import Bot
from database import is_seen, mark_seen
from config import RSS_FEEDS

async def check_and_post(bot: Bot):
    for url in RSS_FEEDS:  # позже заменим на динамические из БД
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:  # проверяем последние 5
            if await is_seen(entry.link):
                continue
            post_text = f"📰 <b>{entry.title}</b>\n\n{entry.get('description', '')[:300]}...\n\n🔗 {entry.link}"
            try:
                await bot.send_message(CHANNEL_ID, post_text, parse_mode="HTML", disable_web_page_preview=False)
                await mark_seen(entry.link)
            except Exception as e:
                print(f"Ошибка постинга: {e}")
