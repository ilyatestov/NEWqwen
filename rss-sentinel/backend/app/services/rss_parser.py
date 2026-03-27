# RSS Parser Service with Image Processing
import feedparser
import aiohttp
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class RSSParserService:
    """Async RSS parsing service with image extraction"""
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.session = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={'User-Agent': 'RSS Sentinel/1.0'},
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
    
    def _parse_feed_sync(self, url: str) -> feedparser.FeedParserDict:
        """Parse feed in thread pool to avoid blocking"""
        return feedparser.parse(url)
    
    async def fetch_feed(self, url: str) -> Dict:
        """Fetch and parse RSS feed"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(self.executor, self._parse_feed_sync, url)
            
            if result.bozo:
                logger.warning(f"Feed parsing warnings for {url}: {result.bozo_exception}")
            
            entries = []
            for entry in result.entries[:20]:  # Limit entries
                parsed_entry = {
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'description': entry.get('description', ''),
                    'published': entry.get('published_parsed', entry.get('updated_parsed')),
                    'author': entry.get('author', ''),
                    'tags': [tag.term for tag in entry.get('tags', [])],
                    'enclosures': [
                        {
                            'href': enc.get('href'),
                            'type': enc.get('type'),
                            'length': enc.get('length')
                        }
                        for enc in entry.get('enclosures', [])
                    ]
                }
                
                # Convert published time
                if parsed_entry['published']:
                    try:
                        parsed_entry['published_dt'] = datetime(
                            *parsed_entry['published'][:6]
                        )
                    except (TypeError, ValueError):
                        parsed_entry['published_dt'] = datetime.utcnow()
                else:
                    parsed_entry['published_dt'] = datetime.utcnow()
                
                entries.append(parsed_entry)
            
            feed_info = {
                'title': result.feed.get('title', ''),
                'description': result.feed.get('description', ''),
                'link': result.feed.get('link', url),
                'entries': entries
            }
            
            logger.info(f"Parsed {len(entries)} entries from {url}")
            return feed_info
            
        except Exception as e:
            logger.error(f"Error parsing feed {url}: {e}")
            raise
    
    async def download_image(self, image_url: str, save_path: str) -> bool:
        """Download image from URL"""
        try:
            session = await self.get_session()
            async with session.get(image_url) as response:
                if response.status == 200:
                    content = await response.read()
                    with open(save_path, 'wb') as f:
                        f.write(content)
                    logger.debug(f"Downloaded image: {image_url}")
                    return True
                else:
                    logger.warning(f"Failed to download image: {image_url} (status {response.status})")
                    return False
        except Exception as e:
            logger.error(f"Error downloading image {image_url}: {e}")
            return False
    
    async def process_images(self, image_urls: List[str], cache_dir: str) -> List[str]:
        """Download multiple images and return local paths"""
        import os
        import hashlib
        from pathlib import Path
        
        os.makedirs(cache_dir, exist_ok=True)
        downloaded_paths = []
        
        tasks = []
        for url in image_urls[:4]:  # Max 4 images
            # Generate unique filename
            img_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            ext = url.split('.')[-1].split('?')[0] or 'jpg'
            filename = f"{img_hash}.{ext}"
            save_path = os.path.join(cache_dir, filename)
            
            if os.path.exists(save_path):
                downloaded_paths.append(save_path)
            else:
                tasks.append((url, save_path))
        
        # Download missing images
        for url, path in tasks:
            success = await self.download_image(url, path)
            if success:
                downloaded_paths.append(path)
        
        return downloaded_paths
    
    def extract_media_from_entry(self, entry: Dict) -> List[str]:
        """Extract all media URLs from parsed entry"""
        images = []
        
        # From enclosures
        for enc in entry.get('enclosures', []):
            if enc.get('type', '').startswith('image/'):
                images.append(enc.get('href'))
        
        # From description/content HTML
        import re
        content = entry.get('description', '') + entry.get('content', [{}])[0].get('value', '')
        img_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
        found = re.findall(img_pattern, content, re.IGNORECASE)
        images.extend(found)
        
        # Deduplicate and clean
        seen = set()
        cleaned = []
        for img in images:
            if img and img not in seen:
                if img.startswith('//'):
                    img = 'https:' + img
                elif img.startswith('/'):
                    continue
                seen.add(img)
                cleaned.append(img)
        
        return cleaned[:4]  # Max 4 images

# Global instance
rss_parser = RSSParserService()
