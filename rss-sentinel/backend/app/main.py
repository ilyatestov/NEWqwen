# FastAPI Application
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List, Optional
import logging
import os

from app.core.config import settings, is_valid_url
from app.db.session import get_db, init_database
from app.services.feed_service import FeedService, StatsService
from app.filters.content_filter import content_filter
from app.services.rss_parser import rss_parser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RSS Sentinel API",
    description="Advanced RSS feed management with filtering and multi-platform publishing",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
@app.on_event("startup")
async def startup_event():
    logger.info("Starting RSS Sentinel...")
    init_database(settings.DATABASE_URL)
    logger.info("Database initialized")

@app.on_event("shutdown")
async def shutdown_event():
    await rss_parser.close()
    logger.info("RSS Sentinel shut down")

# Serve frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "../../frontend/dist")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

# API Routes
@app.get("/")
async def root():
    return {"message": "RSS Sentinel API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": "now"}

@app.post("/api/feeds")
async def add_feed(
    url: str,
    title: Optional[str] = None,
    check_interval: int = 300,
    filter_keywords_include: List[str] = None,
    filter_keywords_exclude: List[str] = None,
    filter_min_length: int = 50,
    telegram_enabled: bool = True,
    telegram_channel_id: Optional[str] = None,
    post_template: Optional[str] = None,
    db = Depends(get_db)
):
    """Add new RSS feed"""
    # Validate URL
    if not is_valid_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL or SSRF detected")
    
    feed_service = FeedService(db)
    try:
        feed = feed_service.add_feed(
            url=url,
            title=title,
            check_interval=check_interval,
            filter_keywords_include=filter_keywords_include,
            filter_keywords_exclude=filter_keywords_exclude,
            filter_min_length=filter_min_length,
            telegram_enabled=telegram_enabled,
            telegram_channel_id=telegram_channel_id,
            post_template=post_template
        )
        return feed
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/feeds")
async def get_feeds(active_only: bool = False, db = Depends(get_db)):
    """Get all RSS feeds"""
    feed_service = FeedService(db)
    return feed_service.get_all_feeds(active_only=active_only)

@app.get("/api/feeds/{feed_id}")
async def get_feed(feed_id: int, db = Depends(get_db)):
    """Get single feed by ID"""
    feed_service = FeedService(db)
    feed = feed_service.get_feed(feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    return feed

@app.delete("/api/feeds/{feed_id}")
async def delete_feed(feed_id: int, db = Depends(get_db)):
    """Delete RSS feed"""
    feed_service = FeedService(db)
    if not feed_service.remove_feed(feed_id):
        raise HTTPException(status_code=404, detail="Feed not found")
    return {"message": "Feed deleted"}

@app.put("/api/feeds/{feed_id}/toggle")
async def toggle_feed(feed_id: int, db = Depends(get_db)):
    """Toggle feed active/inactive"""
    feed_service = FeedService(db)
    feed = feed_service.toggle_feed(feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    return feed

@app.put("/api/feeds/{feed_id}")
async def update_feed(
    feed_id: int,
    title: Optional[str] = None,
    check_interval: Optional[int] = None,
    filter_keywords_include: Optional[List[str]] = None,
    filter_keywords_exclude: Optional[List[str]] = None,
    filter_min_length: Optional[int] = None,
    telegram_enabled: Optional[bool] = None,
    post_template: Optional[str] = None,
    db = Depends(get_db)
):
    """Update feed settings"""
    feed_service = FeedService(db)
    
    update_data = {}
    if title is not None: update_data['title'] = title
    if check_interval is not None: update_data['check_interval'] = check_interval
    if filter_keywords_include is not None: update_data['filter_keywords_include'] = filter_keywords_include
    if filter_keywords_exclude is not None: update_data['filter_keywords_exclude'] = filter_keywords_exclude
    if filter_min_length is not None: update_data['filter_min_length'] = filter_min_length
    if telegram_enabled is not None: update_data['telegram_enabled'] = telegram_enabled
    if post_template is not None: update_data['post_template'] = post_template
    
    feed = feed_service.update_feed(feed_id, **update_data)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    return feed

@app.post("/api/feeds/{feed_id}/check")
async def check_feed_now(feed_id: int, db = Depends(get_db)):
    """Manually trigger feed check"""
    from app.models.database import RSSFeed
    
    feed = db.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    
    # TODO: Trigger immediate check via task queue
    return {"message": "Check scheduled", "feed_id": feed_id}

@app.get("/api/stats")
async def get_stats(db = Depends(get_db)):
    """Get overall statistics"""
    stats_service = StatsService(db)
    return stats_service.get_overall_stats()

@app.get("/api/stats/{feed_id}")
async def get_feed_stats(feed_id: int, db = Depends(get_db)):
    """Get statistics for specific feed"""
    stats_service = StatsService(db)
    stats = stats_service.get_feed_stats(feed_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Feed not found")
    return stats

@app.post("/api/filter/preview")
async def preview_filter(
    title: str,
    content: str,
    link: str,
    filter_keywords_include: List[str] = None,
    filter_keywords_exclude: List[str] = None,
    filter_min_length: int = 50,
    db = Depends(get_db)
):
    """Preview how content will be filtered"""
    feed_config = {
        'enable_duplicate_check': False,  # Skip duplicate check for preview
        'filter_keywords_include': filter_keywords_include or [],
        'filter_keywords_exclude': filter_keywords_exclude or [],
        'filter_min_length': filter_min_length,
        'enable_images': True,
        'max_images_per_post': 4
    }
    
    result = content_filter.process_entry(
        db, title, content, link, feed_config
    )
    
    return result

# Frontend routes
@app.get("/dashboard")
async def dashboard():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Frontend not built"}

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve SPA frontend"""
    if full_path.startswith("api/") or full_path.startswith("docs"):
        raise HTTPException(status_code=404)
    
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Frontend not built"}
