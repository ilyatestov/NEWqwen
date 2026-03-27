"""
FastAPI REST API for RSS Hub management.
"""
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict
import logging

from ..core.config import get_config, is_valid_url
from ..db.database import get_database
from ..services.telegram import get_telegram_service
from ..tasks.scheduler import get_scheduler

logger = logging.getLogger(__name__)


# Pydantic models
class FeedCreate(BaseModel):
    url: str
    title: Optional[str] = None


class FeedResponse(BaseModel):
    id: int
    url: str
    title: Optional[str]
    description: Optional[str]
    is_active: bool
    last_check: Optional[str]
    created_at: str


class StatsResponse(BaseModel):
    total_feeds: int
    total_entries: int
    daily_posts: Dict[str, int]


class HealthResponse(BaseModel):
    status: str
    database: str
    scheduler: str


# API app
app = FastAPI(
    title="RSS Hub API",
    description="REST API for managing RSS feeds and Telegram bot",
    version="1.0.0"
)

# CORS middleware
config = get_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.web.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency injection
def get_db():
    return get_database()


# Routes
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    db = get_database()
    scheduler = get_scheduler()
    
    # Check database
    try:
        db.get_feeds(active_only=False)
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Check scheduler
    scheduler_status = "running" if scheduler._running else "stopped"
    
    return HealthResponse(
        status="healthy" if db_status == "ok" else "unhealthy",
        database=db_status,
        scheduler=scheduler_status
    )


@app.get("/api/feeds", response_model=List[FeedResponse])
async def list_feeds(active_only: bool = False, db=Depends(get_db)):
    """List all RSS feeds."""
    feeds = db.get_feeds(active_only=active_only)
    return [FeedResponse(**feed) for feed in feeds]


@app.get("/api/feeds/{feed_id}", response_model=FeedResponse)
async def get_feed(feed_id: int, db=Depends(get_db)):
    """Get a specific feed by ID."""
    feed = db.get_feed_by_id(feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    return FeedResponse(**feed)


@app.post("/api/feeds", response_model=FeedResponse, status_code=status.HTTP_201_CREATED)
async def create_feed(feed_data: FeedCreate, db=Depends(get_db)):
    """Add a new RSS feed."""
    # Validate URL
    if not is_valid_url(feed_data.url):
        raise HTTPException(
            status_code=400,
            detail="Invalid URL or SSRF protection triggered"
        )
    
    try:
        feed_id = db.add_feed(feed_data.url, feed_data.title)
        feed = db.get_feed_by_id(feed_id)
        return FeedResponse(**feed)
    except Exception as e:
        logger.error(f"Error creating feed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/feeds/{feed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feed(feed_id: int, db=Depends(get_db)):
    """Remove an RSS feed."""
    if not db.remove_feed(feed_id):
        raise HTTPException(status_code=404, detail="Feed not found")


@app.post("/api/feeds/{feed_id}/check")
async def check_feed_now(feed_id: int, db=Depends(get_db)):
    """Trigger immediate check for a specific feed."""
    feed = db.get_feed_by_id(feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    
    scheduler = get_scheduler()
    asyncio.create_task(scheduler.check_feed(feed_id, feed['url']))
    
    return {"status": "checking", "feed_id": feed_id}


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats(db=Depends(get_db)):
    """Get statistics."""
    stats = db.get_statistics(days=30)
    return StatsResponse(**stats)


@app.post("/api/scheduler/start")
async def start_scheduler():
    """Start the feed checker scheduler."""
    scheduler = get_scheduler()
    scheduler.start()
    return {"status": "started"}


@app.post("/api/scheduler/stop")
async def stop_scheduler():
    """Stop the feed checker scheduler."""
    scheduler = get_scheduler()
    scheduler.stop()
    return {"status": "stopped"}


@app.get("/api/scheduler/status")
async def scheduler_status():
    """Get scheduler status."""
    scheduler = get_scheduler()
    return {
        "running": scheduler._running,
        "jobs_count": len(scheduler.scheduler.get_jobs())
    }
