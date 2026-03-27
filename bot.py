import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import BOT_TOKEN, ADMIN_ID, CHANNEL_ID, is_valid_url
from rss_handler import check_and_post
from database import init_db, add_feed_to_db, get_active_feeds, remove_feed_from_db, get_stats

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id == ADMIN_ID

@dp.message(Command("start"))
async def start(message: Message):
    if not is_admin(message.from_user.id):
        logger.warning(f"Несанкционированный доступ от пользователя {message.from_user.id}")
        return
    await message.answer(
        f"✅ <b>Бот запущен!</b>\n\n"
        f"📢 Канал: {CHANNEL_ID}\n"
        f"⏱ Интервал проверки: каждые {scheduler._jobs[0].trigger.interval.total_seconds() if scheduler._jobs else 'N/A'} сек.\n\n"
        f"<b>Команды:</b>\n"
        f"/add &lt;url&gt; — добавить RSS ленту\n"
        f"/remove &lt;url&gt; — удалить RSS ленту\n"
        f"/feeds — список активных лент\n"
        f"/stats — статистика бота"
    )

@dp.message(Command("add"))
async def add_feed(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Использование: /add &lt;URL&gt;")
        return
    
    url = parts[1].strip()
    
    # Валидация URL (защита от SSRF)
    if not is_valid_url(url):
        await message.answer("❌ Неверный URL или доступ к внутренним ресурсам запрещён")
        logger.warning(f"Попытка добавить невалидный URL: {url}")
        return
    
    # Добавляем в БД
    success = await add_feed_to_db(url)
    if success:
        await message.answer(f"✅ Добавлена лента: {url}")
        logger.info(f"Добавлена RSS лента: {url}")
    else:
        await message.answer(f"❌ Ошибка при добавлении ленты: {url}")

@dp.message(Command("remove"))
async def remove_feed(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Использование: /remove &lt;URL&gt;")
        return
    
    url = parts[1].strip()
    success = await remove_feed_from_db(url)
    if success:
        await message.answer(f"✅ Удалена лента: {url}")
        logger.info(f"Удалена RSS лента: {url}")
    else:
        await message.answer(f"❌ Лента не найдена: {url}")

@dp.message(Command("feeds"))
async def list_feeds(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    feeds = await get_active_feeds()
    if not feeds:
        await message.answer("📭 Нет активных RSS лент")
        return
    
    feed_list = "\n".join([f"• {feed}" for feed in feeds])
    await message.answer(f"📡 <b>Активные ленты ({len(feeds)}):</b>\n\n{feed_list}")

@dp.message(Command("stats"))
async def show_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    stats = await get_stats()
    await message.answer(
        f"📊 <b>Статистика бота:</b>\n\n"
        f"📝 Обработано постов: {stats['seen_posts']}\n"
        f"📡 Активных лент: {stats['active_feeds']}"
    )

async def scheduled_check():
    """Обертка для плановой проверки с обработкой ошибок"""
    try:
        await check_and_post(bot)
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в плановой проверке: {e}", exc_info=True)

async def main():
    await init_db()
    
    # Добавляем задачу в планировщик с graceful shutdown
    scheduler.add_job(scheduled_check, "interval", seconds=60, id="rss_check", replace_existing=True)
    scheduler.start()
    
    logger.info("🚀 Бот запущен и проверяет RSS...")
    
    try:
        await dp.start_polling(bot)
    finally:
        # Graceful shutdown
        scheduler.shutdown()
        await bot.session.close()
        logger.info("👋 Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())
