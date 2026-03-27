"""
Database module with connection pooling, migrations, and CRUD operations.
"""
import sqlite3
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from pathlib import Path

from ..core.config import get_config, DatabaseConfig

logger = logging.getLogger(__name__)


class Database:
    """Database manager with connection pooling."""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._pool: List[sqlite3.Connection] = []
        self._initialized = False
        
    def initialize(self):
        """Initialize database and run migrations."""
        if self._initialized:
            return
            
        # Ensure data directory exists
        db_path = Path(self.config.path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create initial connection
        conn = self._create_connection()
        self._run_migrations(conn)
        self._pool.append(conn)
        self._initialized = True
        
        logger.info(f"Database initialized at {self.config.path}")
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection."""
        conn = sqlite3.connect(
            self.config.path,
            timeout=self.config.timeout,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        
        # Enable WAL mode for better concurrency
        if self.config.wal_mode:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
        
        # Set pool size limit
        conn.execute(f"PRAGMA cache_size=-{self.config.pool_size * 1000}")
        
        return conn
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool."""
        if not self._initialized:
            self.initialize()
        
        conn = None
        try:
            if self._pool:
                conn = self._pool.pop()
            else:
                conn = self._create_connection()
            
            yield conn
        finally:
            if conn:
                if len(self._pool) < self.config.pool_size:
                    self._pool.append(conn)
                else:
                    conn.close()
    
    def _run_migrations(self, conn: sqlite3.Connection):
        """Run database migrations."""
        cursor = conn.cursor()
        
        # Feeds table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT,
                description TEXT,
                last_check TIMESTAMP,
                next_check TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Entries table with hash index
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feed_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                link TEXT NOT NULL,
                summary TEXT,
                content TEXT,
                published_at TIMESTAMP,
                hash TEXT NOT NULL,
                posted BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (feed_id) REFERENCES feeds(id) ON DELETE CASCADE
            )
        """)
        
        # Create index on hash for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entries_hash 
            ON entries(hash)
        """)
        
        # Create index on feed_id and posted status
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entries_feed_posted 
            ON entries(feed_id, posted)
        """)
        
        # Statistics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                feed_id INTEGER,
                posts_count INTEGER DEFAULT 0,
                errors_count INTEGER DEFAULT 0,
                UNIQUE(date, feed_id)
            )
        """)
        
        # Settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        logger.debug("Database migrations completed")
    
    def add_feed(self, url: str, title: Optional[str] = None) -> int:
        """Add a new RSS feed."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO feeds (url, title, next_check)
                    VALUES (?, ?, ?)
                """, (url, title, datetime.now()))
                conn.commit()
                feed_id = cursor.lastrowid
                logger.info(f"Added feed {url} with ID {feed_id}")
                return feed_id
            except sqlite3.IntegrityError:
                logger.warning(f"Feed {url} already exists")
                cursor.execute("SELECT id FROM feeds WHERE url = ?", (url,))
                return cursor.fetchone()[0]
    
    def remove_feed(self, feed_id: int) -> bool:
        """Remove an RSS feed."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM feeds WHERE id = ?", (feed_id,))
            conn.commit()
            affected = cursor.rowcount
            if affected:
                logger.info(f"Removed feed with ID {feed_id}")
            return affected > 0
    
    def get_feeds(self, active_only: bool = False) -> List[Dict]:
        """Get all RSS feeds."""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM feeds"
            if active_only:
                query += " WHERE is_active = 1"
            
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_feed_by_id(self, feed_id: int) -> Optional[Dict]:
        """Get a specific feed by ID."""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM feeds WHERE id = ?", (feed_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def entry_exists(self, hash_value: str) -> bool:
        """Check if an entry already exists."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM entries WHERE hash = ?", (hash_value,))
            return cursor.fetchone() is not None
    
    def add_entry(self, feed_id: int, entry_data: Dict) -> int:
        """Add a new entry."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO entries (feed_id, title, link, summary, content, published_at, hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                feed_id,
                entry_data.get('title', ''),
                entry_data.get('link', ''),
                entry_data.get('summary', ''),
                entry_data.get('content', ''),
                entry_data.get('published_at'),
                entry_data['hash']
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_unposted_entries(self, feed_id: Optional[int] = None, limit: int = 50) -> List[Dict]:
        """Get unposted entries."""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if feed_id:
                cursor.execute("""
                    SELECT * FROM entries 
                    WHERE feed_id = ? AND posted = 0 
                    ORDER BY published_at DESC 
                    LIMIT ?
                """, (feed_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM entries 
                    WHERE posted = 0 
                    ORDER BY published_at DESC 
                    LIMIT ?
                """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def mark_entry_posted(self, entry_id: int):
        """Mark an entry as posted."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE entries SET posted = 1 WHERE id = ?", (entry_id,))
            conn.commit()
    
    def update_feed_check(self, feed_id: int, success: bool = True):
        """Update feed check timestamp."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now()
            next_check = now + timedelta(seconds=get_config().bot.check_interval)
            
            if success:
                cursor.execute("""
                    UPDATE feeds 
                    SET last_check = ?, next_check = ?
                    WHERE id = ?
                """, (now, next_check, feed_id))
            else:
                # On error, retry sooner
                next_check = now + timedelta(minutes=5)
                cursor.execute("""
                    UPDATE feeds 
                    SET last_check = ?, next_check = ?
                    WHERE id = ?
                """, (now, next_check, feed_id))
            
            conn.commit()
    
    def cleanup_old_entries(self, days: int = 30):
        """Remove old entries to save space."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff = datetime.now() - timedelta(days=days)
            cursor.execute("""
                DELETE FROM entries 
                WHERE posted = 1 AND created_at < ?
            """, (cutoff,))
            removed = cursor.rowcount
            conn.commit()
            if removed:
                logger.info(f"Cleaned up {removed} old entries")
            return removed
    
    def get_statistics(self, days: int = 7) -> Dict:
        """Get statistics for the last N days."""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cutoff = datetime.now() - timedelta(days=days)
            
            # Total feeds
            cursor.execute("SELECT COUNT(*) FROM feeds WHERE is_active = 1")
            total_feeds = cursor.fetchone()[0]
            
            # Total entries
            cursor.execute("SELECT COUNT(*) FROM entries")
            total_entries = cursor.fetchone()[0]
            
            # Entries per day
            cursor.execute("""
                SELECT date(created_at) as date, COUNT(*) as count
                FROM entries
                WHERE created_at >= ?
                GROUP BY date(created_at)
                ORDER BY date DESC
            """, (cutoff,))
            daily_posts = {row['date']: row['count'] for row in cursor.fetchall()}
            
            return {
                'total_feeds': total_feeds,
                'total_entries': total_entries,
                'daily_posts': daily_posts
            }


# Global database instance
_db: Optional[Database] = None


def get_database() -> Database:
    """Get global database instance."""
    global _db
    if _db is None:
        config = get_config()
        _db = Database(config.database)
        _db.initialize()
    return _db
