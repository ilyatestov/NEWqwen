"""
Background task scheduler for RSS feed checking.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..core.config import get_config
from ..db.database import get_database
from ..services.rss_parser import get_parser
from ..services.telegram import get_telegram_service

logger = logging.getLogger(__name__)


class FeedScheduler:
    """Scheduler for periodic RSS feed checking."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._running = False
        self._tasks: Dict[int, asyncio.Task] = {}
    
    async def check_feed(self, feed_id: int, url: str):
        """Check a single feed for new entries."""
        try:
            logger.info(f"Checking feed {feed_id}: {url}")
            
            db = get_database()
            parser = get_parser()
            telegram = get_telegram_service()
            
            # Parse feed
            entries = await parser.fetch_and_process(url, feed_id)
            
            if not entries:
                db.update_feed_check(feed_id, success=True)
                return
            
            posted_count = 0
            
            for entry in entries:
                # Check if entry already exists
                if db.entry_exists(entry['hash']):
                    continue
                
                # Add to database
                entry_id = db.add_entry(feed_id, entry)
                
                # Post to Telegram
                entry['id'] = entry_id
                if await telegram.post_entry(entry):
                    db.mark_entry_posted(entry_id)
                    posted_count += 1
            
            db.update_feed_check(feed_id, success=True)
            logger.info(f"Feed {feed_id}: processed {len(entries)} entries, posted {posted_count}")
            
        except Exception as e:
            logger.error(f"Error checking feed {feed_id}: {e}")
            db = get_database()
            db.update_feed_check(feed_id, success=False)
    
    async def check_all_feeds(self):
        """Check all active feeds."""
        db = get_database()
        feeds = db.get_feeds(active_only=True)
        
        logger.info(f"Starting check for {len(feeds)} feeds")
        
        # Create tasks for all feeds
        tasks = []
        for feed in feeds:
            if feed['url']:
                task = asyncio.create_task(
                    self.check_feed(feed['id'], feed['url'])
                )
                tasks.append(task)
                self._tasks[feed['id']] = task
        
        # Wait for all tasks with timeout
        if tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=300  # 5 minutes total timeout
                )
            except asyncio.TimeoutError:
                logger.warning("Feed checking timed out")
    
    async def cleanup_task(self):
        """Periodic cleanup of old entries."""
        try:
            db = get_database()
            removed = db.cleanup_old_entries(days=30)
            if removed:
                logger.info(f"Cleanup removed {removed} old entries")
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
    
    def start(self):
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        config = get_config()
        
        # Schedule feed checking
        check_interval = config.bot.check_interval
        self.scheduler.add_job(
            self.check_all_feeds,
            trigger=IntervalTrigger(seconds=check_interval),
            id='check_feeds',
            name='Check all RSS feeds',
            replace_existing=True
        )
        
        # Schedule daily cleanup
        self.scheduler.add_job(
            self.cleanup_task,
            trigger=IntervalTrigger(hours=24),
            id='cleanup',
            name='Cleanup old entries',
            replace_existing=True
        )
        
        self.scheduler.start()
        self._running = True
        
        logger.info(f"Scheduler started with {check_interval}s interval")
    
    def stop(self):
        """Stop the scheduler."""
        if not self._running:
            return
        
        self.scheduler.shutdown(wait=False)
        self._running = False
        
        # Cancel pending tasks
        for task in self._tasks.values():
            if not task.done():
                task.cancel()
        
        self._tasks.clear()
        logger.info("Scheduler stopped")
    
    async def run_once(self):
        """Run feed check once (for testing)."""
        await self.check_all_feeds()


# Global scheduler instance
_scheduler: Optional[FeedScheduler] = None


def get_scheduler() -> FeedScheduler:
    """Get global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = FeedScheduler()
    return _scheduler
