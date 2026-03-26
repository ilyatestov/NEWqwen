"""
Main application entry point.
"""
import asyncio
import logging
import signal
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class Application:
    """Main application manager."""
    
    def __init__(self):
        self._shutdown_event = asyncio.Event()
        self._tasks = []
    
    async def initialize(self):
        """Initialize all components."""
        logger.info("Initializing RSS Hub...")
        
        # Initialize database
        from ..app.db.database import get_database
        db = get_database()
        logger.info("Database initialized")
        
        # Initialize Telegram bot
        from ..app.services.telegram import get_telegram_service
        telegram = get_telegram_service()
        await telegram.initialize()
        logger.info("Telegram service initialized")
        
        # Initialize scheduler
        from ..app.tasks.scheduler import get_scheduler
        scheduler = get_scheduler()
        scheduler.start()
        logger.info("Scheduler started")
        
        logger.info("RSS Hub initialization complete")
    
    async def run(self):
        """Run the application."""
        await self.initialize()
        
        # Start Telegram bot polling
        from ..app.services.telegram import get_telegram_service
        telegram = get_telegram_service()
        
        # Run bot in background
        bot_task = asyncio.create_task(telegram.start_polling())
        self._tasks.append(bot_task)
        
        # Wait for shutdown signal
        await self._shutdown_event.wait()
        
        logger.info("Shutdown signal received")
    
    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("Shutting down RSS Hub...")
        
        # Stop scheduler
        from ..app.tasks.scheduler import get_scheduler
        scheduler = get_scheduler()
        scheduler.stop()
        
        # Stop Telegram bot
        from ..app.services.telegram import get_telegram_service
        telegram = get_telegram_service()
        await telegram.stop()
        
        # Cancel pending tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        # Close parser
        from ..app.services.rss_parser import get_parser
        parser = get_parser()
        parser.close()
        
        logger.info("RSS Hub shutdown complete")
    
    def request_shutdown(self):
        """Request application shutdown."""
        self._shutdown_event.set()


# Global application instance
_app: Optional[Application] = None


def get_application() -> Application:
    """Get global application instance."""
    global _app
    if _app is None:
        _app = Application()
    return _app


async def main():
    """Main entry point."""
    app = get_application()
    
    # Setup signal handlers
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        logger.info("Received shutdown signal")
        app.request_shutdown()
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)
    
    try:
        await app.run()
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise
    finally:
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
