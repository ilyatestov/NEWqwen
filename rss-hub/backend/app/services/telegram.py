"""
Telegram Bot Service with message formatting and retry logic.
"""
import asyncio
import logging
from typing import Optional, List, Dict
from datetime import datetime

try:
    import aiohttp
    from aiogram import Bot, Dispatcher, types
    from aiogram.filters import Command
    from aiogram.types import ParseMode
except ImportError:
    # Fallback for testing without aiogram
    Bot = None
    Dispatcher = None

from ..core.config import get_config, BotConfig
from ..db.database import get_database

logger = logging.getLogger(__name__)


class TelegramService:
    """Telegram bot service with retry logic."""
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self):
        """Initialize bot and session."""
        if Bot is None:
            logger.warning("aiogram not installed, running in mock mode")
            return
        
        self._session = aiohttp.ClientSession()
        self.bot = Bot(token=self.config.token, session=self._session)
        self.dp = Dispatcher()
        
        # Register handlers
        self.dp.message(Command("start"))(self.cmd_start)
        self.dp.message(Command("help"))(self.cmd_help)
        self.dp.message(Command("feeds"))(self.cmd_feeds)
        self.dp.message(Command("add"))(self.cmd_add)
        self.dp.message(Command("remove"))(self.cmd_remove)
        self.dp.message(Command("stats"))(self.cmd_stats)
        
        logger.info("Telegram bot initialized")
    
    async def cmd_start(self, message: types.Message):
        """Handle /start command."""
        if message.from_user.id not in self.config.admin_ids:
            return
        
        await message.answer(
            "👋 Welcome to RSS Hub!\n\n"
            "Available commands:\n"
            "/help - Show help\n"
            "/feeds - List all feeds\n"
            "/add <url> - Add new feed\n"
            "/remove <id> - Remove feed\n"
            "/stats - Show statistics"
        )
    
    async def cmd_help(self, message: types.Message):
        """Handle /help command."""
        if message.from_user.id not in self.config.admin_ids:
            return
        
        await message.answer(
            "📚 RSS Hub Help\n\n"
            "**Managing Feeds:**\n"
            "/feeds - List all RSS feeds\n"
            "/add <url> [title] - Add new feed\n"
            "/remove <id> - Remove feed by ID\n\n"
            "**Statistics:**\n"
            "/stats - Show bot statistics\n\n"
            "**Other:**\n"
            "/start - Welcome message"
        )
    
    async def cmd_feeds(self, message: types.Message):
        """Handle /feeds command."""
        if message.from_user.id not in self.config.admin_ids:
            return
        
        db = get_database()
        feeds = db.get_feeds()
        
        if not feeds:
            await message.answer("📭 No feeds configured yet.")
            return
        
        text = "📡 **Active Feeds:**\n\n"
        for feed in feeds:
            status = "✅" if feed['is_active'] else "❌"
            text += f"{status} `{feed['id']}` - {feed['title'] or 'Untitled'}\n"
            text += f"   URL: `{feed['url']}`\n\n"
        
        await message.answer(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_add(self, message: types.Message):
        """Handle /add command."""
        if message.from_user.id not in self.config.admin_ids:
            return
        
        from ..core.config import is_valid_url
        
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer("Usage: /add <url> [title]")
            return
        
        url = args[1].split()[0]  # Get URL only
        title = ' '.join(args[1].split()[1:]) if len(args[1].split()) > 1 else None
        
        if not is_valid_url(url):
            await message.answer("❌ Invalid URL or SSRF protection triggered.")
            return
        
        try:
            db = get_database()
            feed_id = db.add_feed(url, title)
            await message.answer(f"✅ Feed added successfully! ID: `{feed_id}`", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Error adding feed: {e}")
            await message.answer(f"❌ Error adding feed: {str(e)}")
    
    async def cmd_remove(self, message: types.Message):
        """Handle /remove command."""
        if message.from_user.id not in self.config.admin_ids:
            return
        
        args = message.text.split()
        if len(args) < 2:
            await message.answer("Usage: /remove <feed_id>")
            return
        
        try:
            feed_id = int(args[1])
            db = get_database()
            
            if db.remove_feed(feed_id):
                await message.answer(f"✅ Feed {feed_id} removed.")
            else:
                await message.answer(f"❌ Feed {feed_id} not found.")
        except ValueError:
            await message.answer("❌ Invalid feed ID. Must be a number.")
        except Exception as e:
            logger.error(f"Error removing feed: {e}")
            await message.answer(f"❌ Error: {str(e)}")
    
    async def cmd_stats(self, message: types.Message):
        """Handle /stats command."""
        if message.from_user.id not in self.config.admin_ids:
            return
        
        db = get_database()
        stats = db.get_statistics()
        
        text = (
            "📊 **RSS Hub Statistics**\n\n"
            f"📡 Active Feeds: `{stats['total_feeds']}`\n"
            f"📝 Total Entries: `{stats['total_entries']}`\n\n"
            "**Recent Activity:**\n"
        )
        
        for date, count in list(stats['daily_posts'].items())[:7]:
            text += f"{date}: {count} posts\n"
        
        await message.answer(text, parse_mode=ParseMode.MARKDOWN)
    
    async def send_message(self, chat_id: int, text: str, parse_mode: str = "HTML"):
        """Send message with retry logic."""
        if not self.bot:
            logger.info(f"[MOCK] Would send to {chat_id}: {text[:100]}...")
            return True
        
        max_retries = self.config.max_retries
        delay = self.config.retry_delay
        
        for attempt in range(max_retries):
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=parse_mode,
                    disable_web_page_preview=True
                )
                return True
            except Exception as e:
                logger.warning(f"Send message attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay * (attempt + 1))
        
        logger.error(f"Failed to send message after {max_retries} attempts")
        return False
    
    async def post_entry(self, entry: Dict, channel_id: Optional[str] = None):
        """Post RSS entry to channel."""
        target = channel_id or self.config.channel_id
        if not target:
            logger.warning("No channel ID configured")
            return False
        
        # Format message
        title = entry.get('title', 'No title')
        link = entry.get('link', '')
        summary = entry.get('summary', '')
        
        # Truncate summary if too long
        if len(summary) > 1000:
            summary = summary[:997] + "..."
        
        message = f"<b>{title}</b>\n\n"
        if summary:
            message += f"{summary}\n\n"
        message += f"<a href='{link}'>Read more</a>"
        
        return await self.send_message(target, message)
    
    async def start_polling(self):
        """Start bot polling."""
        if not self.dp:
            logger.warning("Bot not initialized, skipping polling")
            return
        
        logger.info("Starting bot polling...")
        await self.dp.start_polling(self.bot)
    
    async def stop(self):
        """Stop bot and cleanup."""
        if self.bot:
            await self.bot.session.close()
        if self._session:
            await self._session.close()
        logger.info("Telegram bot stopped")


# Global service instance
_service: Optional[TelegramService] = None


def get_telegram_service() -> TelegramService:
    """Get global Telegram service instance."""
    global _service
    if _service is None:
        config = get_config()
        _service = TelegramService(config.bot)
    return _service
