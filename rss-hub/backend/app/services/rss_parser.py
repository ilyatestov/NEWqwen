"""
RSS Feed Parser Service with async support and content sanitization.
"""
import asyncio
import hashlib
import logging
import feedparser
from datetime import datetime
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup, NavigableString

from ..core.config import get_config, RSSConfig

logger = logging.getLogger(__name__)


class RSSParser:
    """Async RSS feed parser with content sanitization."""
    
    def __init__(self, config: RSSConfig):
        self.config = config
        self._executor = ThreadPoolExecutor(max_workers=5)
    
    def _parse_feed_sync(self, url: str) -> feedparser.FeedParserDict:
        """Parse RSS feed in a thread pool."""
        return feedparser.parse(
            url,
            user_agent=self.config.user_agent,
            request_timeout=self.config.timeout
        )
    
    async def parse_feed(self, url: str) -> Optional[Dict]:
        """Parse RSS feed asynchronously."""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._executor,
                self._parse_feed_sync,
                url
            )
            
            if result.bozo:
                logger.warning(f"Feed parsing warnings for {url}: {result.bozo_exception}")
            
            if not result.entries:
                logger.warning(f"No entries found in feed {url}")
                return None
            
            return {
                'title': result.feed.get('title', ''),
                'description': result.feed.get('description', ''),
                'link': result.feed.get('link', url),
                'entries': result.entries
            }
        except Exception as e:
            logger.error(f"Error parsing feed {url}: {e}")
            return None
    
    def _generate_hash(self, link: str) -> str:
        """Generate SHA-256 hash for entry uniqueness."""
        return hashlib.sha256(link.encode()).hexdigest()
    
    def _sanitize_html(self, html: str) -> str:
        """Sanitize HTML content to prevent XSS."""
        if not html:
            return ''
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove blocked tags
            for tag_name in self.config.blocked_tags:
                for tag in soup.find_all(tag_name):
                    tag.decompose()
            
            # Keep only allowed attributes
            allowed_attrs = ['href', 'src', 'alt', 'title']
            for tag in soup.find_all(True):
                attrs = dict(tag.attrs)
                for attr in attrs:
                    if attr not in allowed_attrs:
                        del tag.attrs[attr]
            
            # Clean dangerous URL schemes
            for tag in soup.find_all(['a', 'img']):
                for attr in ['href', 'src']:
                    if attr in tag.attrs:
                        value = tag.attrs[attr]
                        if value.lower().startswith(('javascript:', 'data:', 'vbscript:')):
                            del tag.attrs[attr]
            
            return str(soup)
        except Exception as e:
            logger.error(f"Error sanitizing HTML: {e}")
            return html
    
    def _parse_date(self, date_tuple) -> Optional[datetime]:
        """Parse date from feedparser."""
        if not date_tuple:
            return None
        try:
            return datetime(*date_tuple[:6])
        except Exception:
            return datetime.now()
    
    async def extract_entries(self, feed_data: Dict, feed_id: int) -> List[Dict]:
        """Extract and process entries from parsed feed."""
        entries = []
        
        for item in feed_data.get('entries', [])[:self.config.max_entries_per_feed]:
            try:
                link = item.get('link', '')
                if not link:
                    continue
                
                # Skip if already exists (hash check done in DB layer)
                hash_value = self._generate_hash(link)
                
                title = item.get('title', 'No title')
                
                # Get summary/content
                summary = ''
                content = ''
                
                if 'summary' in item:
                    summary = self._sanitize_html(item.summary)
                
                if 'content' in item and item.content:
                    content = self._sanitize_html(item.content[0].value)
                
                # Parse publication date
                published_at = None
                if 'published_parsed' in item:
                    published_at = self._parse_date(item.published_parsed)
                elif 'updated_parsed' in item:
                    published_at = self._parse_date(item.updated_parsed)
                
                entry_data = {
                    'feed_id': feed_id,
                    'title': title,
                    'link': link,
                    'summary': summary,
                    'content': content,
                    'published_at': published_at,
                    'hash': hash_value
                }
                
                entries.append(entry_data)
                
            except Exception as e:
                logger.error(f"Error processing entry: {e}")
                continue
        
        logger.info(f"Extracted {len(entries)} entries from feed")
        return entries
    
    async def fetch_and_process(self, url: str, feed_id: int) -> List[Dict]:
        """Complete flow: fetch, parse, and process feed."""
        feed_data = await self.parse_feed(url)
        if not feed_data:
            return []
        
        return await self.extract_entries(feed_data, feed_id)
    
    def close(self):
        """Cleanup resources."""
        self._executor.shutdown(wait=False)


# Global parser instance
_parser: Optional[RSSParser] = None


def get_parser() -> RSSParser:
    """Get global parser instance."""
    global _parser
    if _parser is None:
        config = get_config()
        _parser = RSSParser(config.rss)
    return _parser
