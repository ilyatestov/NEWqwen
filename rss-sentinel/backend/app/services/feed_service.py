# Feed Management Service
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FeedService:
    """Service for managing RSS feeds"""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def add_feed(
        self,
        url: str,
        title: Optional[str] = None,
        check_interval: int = 300,
        filter_keywords_include: List[str] = None,
        filter_keywords_exclude: List[str] = None,
        filter_min_length: int = 50,
        telegram_enabled: bool = True,
        telegram_channel_id: Optional[str] = None,
        post_template: str = None
    ) -> Dict:
        """Add new RSS feed"""
        from app.models.database import RSSFeed, FeedStats
        
        # Check if feed already exists
        existing = self.db.query(RSSFeed).filter(RSSFeed.url == url).first()
        if existing:
            raise ValueError(f"Feed with URL {url} already exists")
        
        feed = RSSFeed(
            url=url,
            title=title,
            check_interval=check_interval,
            filter_keywords_include=filter_keywords_include or [],
            filter_keywords_exclude=filter_keywords_exclude or [],
            filter_min_length=filter_min_length,
            telegram_enabled=telegram_enabled,
            telegram_channel_id=telegram_channel_id,
            post_template=post_template or "{title}\n\n{content}\n\n{link}"
        )
        
        self.db.add(feed)
        self.db.commit()
        self.db.refresh(feed)
        
        # Create stats record
        stats = FeedStats(feed_id=feed.id)
        self.db.add(stats)
        self.db.commit()
        
        logger.info(f"Added feed: {feed.title} ({url})")
        
        return self._feed_to_dict(feed)
    
    def remove_feed(self, feed_id: int) -> bool:
        """Remove RSS feed"""
        from app.models.database import RSSFeed
        
        feed = self.db.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
        if not feed:
            return False
        
        self.db.delete(feed)
        self.db.commit()
        logger.info(f"Removed feed ID: {feed_id}")
        return True
    
    def update_feed(self, feed_id: int, **kwargs) -> Optional[Dict]:
        """Update feed settings"""
        from app.models.database import RSSFeed
        
        feed = self.db.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
        if not feed:
            return None
        
        for key, value in kwargs.items():
            if hasattr(feed, key):
                setattr(feed, value)
        
        self.db.commit()
        self.db.refresh(feed)
        
        return self._feed_to_dict(feed)
    
    def get_feed(self, feed_id: int) -> Optional[Dict]:
        """Get single feed by ID"""
        from app.models.database import RSSFeed
        
        feed = self.db.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
        if not feed:
            return None
        
        return self._feed_to_dict(feed)
    
    def get_all_feeds(self, active_only: bool = False) -> List[Dict]:
        """Get all feeds"""
        from app.models.database import RSSFeed
        
        query = self.db.query(RSSFeed)
        if active_only:
            query = query.filter(RSSFeed.is_active == True)
        
        feeds = query.all()
        return [self._feed_to_dict(f) for f in feeds]
    
    def toggle_feed(self, feed_id: int) -> Optional[Dict]:
        """Toggle feed active/inactive"""
        from app.models.database import RSSFeed
        
        feed = self.db.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
        if not feed:
            return None
        
        feed.is_active = not feed.is_active
        self.db.commit()
        self.db.refresh(feed)
        
        logger.info(f"Toggled feed {feed_id} to {'active' if feed.is_active else 'inactive'}")
        return self._feed_to_dict(feed)
    
    def _feed_to_dict(self, feed) -> Dict:
        """Convert feed model to dict"""
        return {
            'id': feed.id,
            'url': feed.url,
            'title': feed.title,
            'description': feed.description,
            'is_active': feed.is_active,
            'check_interval': feed.check_interval,
            'last_check': feed.last_check.isoformat() if feed.last_check else None,
            'filter_keywords_include': feed.filter_keywords_include,
            'filter_keywords_exclude': feed.filter_keywords_exclude,
            'filter_min_length': feed.filter_min_length,
            'telegram_enabled': feed.telegram_enabled,
            'telegram_channel_id': feed.telegram_channel_id,
            'vk_enabled': feed.vk_enabled,
            'twitter_enabled': feed.twitter_enabled,
            'post_template': feed.post_template,
            'created_at': feed.created_at.isoformat() if feed.created_at else None
        }


class StatsService:
    """Service for statistics and analytics"""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def get_overall_stats(self) -> Dict:
        """Get overall system statistics"""
        from app.models.database import RSSFeed, RSSEntry, FeedStats
        
        total_feeds = self.db.query(RSSFeed).count()
        active_feeds = self.db.query(RSSFeed).filter(RSSFeed.is_active == True).count()
        
        total_entries = self.db.query(RSSEntry).count()
        published_entries = self.db.query(RSSEntry).filter(RSSEntry.is_published == True).count()
        
        # Get entries by day (last 7 days)
        from sqlalchemy import func
        from datetime import timedelta
        
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        daily_stats = self.db.query(
            func.date(RSSEntry.created_at).label('date'),
            func.count(RSSEntry.id).label('count')
        ).filter(
            RSSEntry.created_at >= seven_days_ago
        ).group_by(
            func.date(RSSEntry.created_at)
        ).all()
        
        daily_dict = {str(row.date): row.count for row in daily_stats}
        
        return {
            'total_feeds': total_feeds,
            'active_feeds': active_feeds,
            'total_entries': total_entries,
            'published_entries': published_entries,
            'filtered_entries': total_entries - published_entries,
            'daily_stats': daily_dict
        }
    
    def get_feed_stats(self, feed_id: int) -> Optional[Dict]:
        """Get statistics for specific feed"""
        from app.models.database import RSSFeed, RSSEntry, FeedStats
        
        feed = self.db.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
        if not feed:
            return None
        
        stats = self.db.query(FeedStats).filter(FeedStats.feed_id == feed_id).first()
        
        total_entries = self.db.query(RSSEntry).filter(RSSEntry.feed_id == feed_id).count()
        published_entries = self.db.query(RSSEntry).filter(
            RSSEntry.feed_id == feed_id,
            RSSEntry.is_published == True
        ).count()
        
        return {
            'feed_id': feed_id,
            'feed_title': feed.title,
            'total_entries': total_entries,
            'published_entries': published_entries,
            'filtered_entries': total_entries - published_entries,
            'last_check': feed.last_check.isoformat() if feed.last_check else None,
            'daily_stats': stats.daily_stats if stats else {}
        }
