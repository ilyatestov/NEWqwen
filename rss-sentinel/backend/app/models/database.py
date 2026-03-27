"""Database models for RSS Sentinel."""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import hashlib

Base = declarative_base()


class Feed(Base):
    """RSS Feed model with filtering and platform settings."""
    __tablename__ = 'feeds'
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(2048), unique=True, nullable=False, index=True)
    title = Column(String(512))
    description = Column(Text)
    last_check = Column(DateTime, nullable=True)
    next_check = Column(DateTime, nullable=True)
    check_interval = Column(Integer, default=300)  # seconds
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Filters
    filter_keywords_include = Column(JSON, default=list)  # Must contain at least one
    filter_keywords_exclude = Column(JSON, default=list)  # Must not contain any
    filter_min_length = Column(Integer, default=50)
    filter_regex_patterns = Column(JSON, default=list)
    
    # Platform settings
    telegram_enabled = Column(Boolean, default=True)
    telegram_channel_id = Column(String(256), nullable=True)
    vk_enabled = Column(Boolean, default=False)
    vk_group_id = Column(String(256), nullable=True)
    twitter_enabled = Column(Boolean, default=False)
    
    # Post template
    post_template = Column(Text, default="{title}\n\n{content}\n\n{link}")
    
    # Relationships
    posts = relationship("Post", back_populates="feed", cascade="all, delete-orphan", lazy="dynamic")
    stats = relationship("FeedStats", back_populates="feed", uselist=False, cascade="all, delete-orphan")
    filter_rules = relationship("FilterRule", back_populates="feed", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Feed(id={self.id}, url={self.url[:50]}..., active={self.is_active})>"
    
    __table_args__ = (
        Index('idx_feed_url', 'url'),
        Index('idx_feed_active', 'is_active', 'next_check'),
    )


class Post(Base):
    """Parsed RSS post/article with deduplication."""
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True, index=True)
    feed_id = Column(Integer, ForeignKey('feeds.id'), nullable=False)
    
    # Content
    entry_id = Column(String(512), nullable=False)  # Original RSS entry ID
    title = Column(String(1024), nullable=False)
    content = Column(Text)
    description = Column(Text)
    link = Column(String(2048), nullable=False)
    author = Column(String(256), nullable=True)
    published_at = Column(DateTime, nullable=True, index=True)
    
    # Deduplication - SHA-256 hash
    content_hash = Column(String(64), nullable=False, index=True)
    
    # Media
    images = Column(JSON, default=list)  # List of image URLs
    has_media = Column(Boolean, default=False)
    
    # Status
    is_published = Column(Boolean, default=False, index=True)
    published_to_telegram = Column(Boolean, default=False)
    published_to_vk = Column(Boolean, default=False)
    published_to_twitter = Column(Boolean, default=False)
    published_at_platform = Column(DateTime, nullable=True)
    
    # Filtering
    filter_score = Column(Float, default=0.0)  # Relevance score 0-100
    filtered_reason = Column(String(256), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    feed = relationship("Feed", back_populates="posts")
    
    @classmethod
    def generate_hash(cls, link: str, title: str = "") -> str:
        """Generate SHA-256 hash for deduplication."""
        content = f"{link}:{title}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def __repr__(self):
        return f"<Post(id={self.id}, title={self.title[:30]}..., hash={self.content_hash[:8]})>"
    
    __table_args__ = (
        Index('idx_post_hash', 'content_hash'),
        Index('idx_post_feed_published', 'feed_id', 'is_published'),
        Index('idx_post_published_at', 'published_at'),
    )


class FilterRule(Base):
    """Advanced filtering rules for feeds."""
    __tablename__ = 'filter_rules'
    
    id = Column(Integer, primary_key=True, index=True)
    feed_id = Column(Integer, ForeignKey('feeds.id'), nullable=False)
    
    name = Column(String(256), nullable=False)
    rule_type = Column(String(64), nullable=False)  # 'whitelist', 'blacklist', 'regex', 'min_length'
    pattern = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # Higher priority rules apply first
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    feed = relationship("Feed", back_populates="filter_rules")
    
    def __repr__(self):
        return f"<FilterRule(id={self.id}, type={self.rule_type}, pattern={self.pattern[:30]}...)>"


class FeedStats(Base):
    """Statistics for each feed."""
    __tablename__ = 'feed_stats'
    
    id = Column(Integer, primary_key=True)
    feed_id = Column(Integer, ForeignKey('feeds.id'), unique=True, nullable=False)
    
    total_posts = Column(Integer, default=0)
    published_posts = Column(Integer, default=0)
    filtered_posts = Column(Integer, default=0)
    last_published_at = Column(DateTime, nullable=True)
    
    # Daily stats (JSON: {"YYYY-MM-DD": count})
    daily_stats = Column(JSON, default=dict)
    
    # Error tracking
    consecutive_errors = Column(Integer, default=0)
    last_error_at = Column(DateTime, nullable=True)
    last_error_message = Column(Text, nullable=True)
    
    # Relationships
    feed = relationship("Feed", back_populates="stats")
    
    def __repr__(self):
        return f"<FeedStats(feed_id={self.feed_id}, published={self.published_posts})>"


class AuditLog(Base):
    """Audit log for tracking all actions."""
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(64), nullable=False, index=True)  # e.g., "feed_added", "post_published"
    entity_type = Column(String(64), nullable=True)  # e.g., "feed", "post", "user"
    entity_id = Column(Integer, nullable=True)
    user_id = Column(String(64), nullable=True)  # Admin ID or "system"
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action})>"


class UserSettings(Base):
    """User-specific settings for the dashboard."""
    __tablename__ = 'user_settings'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(64), unique=True, nullable=False)  # Telegram ID or username
    
    # UI preferences
    theme = Column(String(32), default="dark")  # light/dark
    timezone = Column(String(64), default="UTC")
    language = Column(String(16), default="en")
    
    # Notification settings
    notify_on_publish = Column(Boolean, default=True)
    notify_on_error = Column(Boolean, default=True)
    digest_enabled = Column(Boolean, default=False)
    digest_time = Column(String(16), nullable=True)  # HH:MM format
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<UserSettings(user_id={self.user_id}, theme={self.theme})>"


# Composite indexes for performance
Index('ix_posts_feed_hash', Post.feed_id, Post.content_hash)
Index('ix_feeds_active_check', Feed.is_active, Feed.next_check)
Index('ix_audit_action_time', AuditLog.action, AuditLog.created_at)
