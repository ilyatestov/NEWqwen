# Advanced Content Filtering Engine
import hashlib
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ContentFilter:
    """Advanced filtering engine for RSS content"""
    
    def __init__(self):
        self.stopwords_cache = {}
    
    def calculate_content_hash(self, title: str, content: str, link: str) -> str:
        """Generate SHA-256 hash for deduplication"""
        combined = f"{title}|{content}|{link}".encode('utf-8')
        return hashlib.sha256(combined).hexdigest()
    
    def check_duplicate(self, session, content_hash: str, days: int = 7) -> bool:
        """Check if content already exists in database"""
        from app.models.database import RSSEntry
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        existing = session.query(RSSEntry).filter(
            RSSEntry.content_hash == content_hash,
            RSSEntry.created_at >= cutoff_date
        ).first()
        
        return existing is not None
    
    def filter_by_keywords(
        self,
        title: str,
        content: str,
        include_keywords: List[str],
        exclude_keywords: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """
        Filter content by keywords.
        Returns (passed_filter, reason_if_filtered)
        """
        text = f"{title} {content}".lower()
        
        # Check exclude keywords (blacklist)
        for keyword in exclude_keywords:
            if keyword.lower() in text:
                reason = f"Contains excluded keyword: {keyword}"
                logger.debug(f"Content filtered: {reason}")
                return False, reason
        
        # Check include keywords (whitelist) - at least one must match
        if include_keywords:
            matched = any(keyword.lower() in text for keyword in include_keywords)
            if not matched:
                reason = f"No matching keywords from: {include_keywords}"
                logger.debug(f"Content filtered: {reason}")
                return False, reason
        
        return True, None
    
    def filter_by_length(self, content: str, min_length: int) -> Tuple[bool, Optional[str]]:
        """Filter by minimum content length"""
        if len(content) < min_length:
            reason = f"Content too short: {len(content)} < {min_length}"
            logger.debug(f"Content filtered: {reason}")
            return False, reason
        return True, None
    
    def filter_by_regex(self, text: str, patterns: List[str]) -> Tuple[bool, Optional[str]]:
        """Filter by regex patterns (any match excludes the content)"""
        for pattern in patterns:
            try:
                if re.search(pattern, text, re.IGNORECASE):
                    reason = f"Matches regex pattern: {pattern}"
                    logger.debug(f"Content filtered: {reason}")
                    return False, reason
            except re.error as e:
                logger.error(f"Invalid regex pattern {pattern}: {e}")
        return True, None
    
    def calculate_relevance_score(
        self,
        title: str,
        content: str,
        keywords: List[str]
    ) -> float:
        """Calculate relevance score based on keyword matches"""
        if not keywords:
            return 0.5  # Neutral score
        
        text = f"{title} {content}".lower()
        score = 0.0
        
        for keyword in keywords:
            if keyword.lower() in text:
                score += 1.0
                # Bonus for title matches
                if keyword.lower() in title.lower():
                    score += 0.5
        
        # Normalize score
        max_score = len(keywords) * 1.5
        return score / max_score if max_score > 0 else 0.0
    
    def extract_images(self, content: str, max_images: int = 4) -> List[str]:
        """Extract image URLs from HTML content"""
        img_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
        images = re.findall(img_pattern, content, re.IGNORECASE)
        
        # Clean up relative URLs (basic handling)
        cleaned = []
        for img in images[:max_images]:
            if img.startswith('//'):
                img = 'https:' + img
            elif img.startswith('/'):
                continue  # Skip relative paths for now
            cleaned.append(img)
        
        return cleaned
    
    def sanitize_html(self, html: str) -> str:
        """Remove dangerous HTML tags while preserving formatting"""
        from bs4 import BeautifulSoup, NavigableString
        
        allowed_tags = ['p', 'br', 'strong', 'b', 'em', 'i', 'u', 'ul', 'ol', 'li', 'a', 'img']
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script, style, and other dangerous tags
        for tag in soup(['script', 'style', 'iframe', 'object', 'embed', 'form']):
            tag.decompose()
        
        # Remove dangerous attributes
        for tag in soup.find_all(True):
            attrs = dict(tag.attrs)
            for attr in attrs:
                if attr.startswith('on') or attr.lower() in ['javascript']:
                    del tag[attr]
        
        return str(soup)
    
    def process_entry(
        self,
        session,
        title: str,
        content: str,
        link: str,
        feed_config: Dict
    ) -> Dict:
        """
        Complete processing pipeline for an RSS entry.
        Returns dict with processing results.
        """
        result = {
            'should_publish': False,
            'filtered_reason': None,
            'content_hash': None,
            'relevance_score': 0.0,
            'images': [],
            'sanitized_content': content
        }
        
        # Generate hash for deduplication
        content_hash = self.calculate_content_hash(title, content, link)
        result['content_hash'] = content_hash
        
        # Check for duplicates
        if feed_config.get('enable_duplicate_check', True):
            is_duplicate = self.check_duplicate(
                session,
                content_hash,
                feed_config.get('duplicate_history_days', 7)
            )
            if is_duplicate:
                result['filtered_reason'] = "Duplicate content"
                logger.debug(f"Entry filtered (duplicate): {title}")
                return result
        
        # Apply filters
        include_keywords = feed_config.get('filter_keywords_include', [])
        exclude_keywords = feed_config.get('filter_keywords_exclude', [])
        min_length = feed_config.get('filter_min_length', 50)
        
        passed, reason = self.filter_by_keywords(
            title, content, include_keywords, exclude_keywords
        )
        if not passed:
            result['filtered_reason'] = reason
            return result
        
        passed, reason = self.filter_by_length(content, min_length)
        if not passed:
            result['filtered_reason'] = reason
            return result
        
        # Calculate relevance score
        result['relevance_score'] = self.calculate_relevance_score(
            title, content, include_keywords
        )
        
        # Extract images
        if feed_config.get('enable_images', True):
            result['images'] = self.extract_images(
                content,
                feed_config.get('max_images_per_post', 4)
            )
        
        # Sanitize HTML
        result['sanitized_content'] = self.sanitize_html(content)
        
        # All checks passed
        result['should_publish'] = True
        logger.info(f"Entry approved for publishing: {title}")
        
        return result

# Global instance
content_filter = ContentFilter()
