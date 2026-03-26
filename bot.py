import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import BOT_TOKEN, ADMIN_ID, CHANNEL_ID, RSS_FEEDS
from rss_handler import check_and_post
from database import init_db

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

@dp.message(Command("start"))
async def start(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(f"✅ Бот запущен! Постим в канал {CHANNEL_ID}\n/add <url> — добавить RSS")

@dp.message(Command("add"))
async def add_feed(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    url = message.text.split(maxsplit=1)[1].strip()
    # Здесь можно добавить в список или БД
    await message.answer(f"✅ Добавлена лента: {url}")

async def main():
    await init_db()
    scheduler.add_job(check_and_post, "interval", seconds=CHECK_INTERVAL, args=[bot])
    scheduler.start()
    print("🚀 Бот запущен и проверяет RSS...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
