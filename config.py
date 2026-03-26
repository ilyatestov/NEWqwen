from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 900))

RSS_FEEDS = [
    # Добавляй свои ленты здесь или через команду /add
    "https://lenta.ru/rss ",
    "https://habr.com/ru/rss/interesting/ ",
    # "https://news.ycombinator.com/rss " и т.д.
]
