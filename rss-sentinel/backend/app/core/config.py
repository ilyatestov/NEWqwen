# Core Configuration & Settings
import os
from pydantic import BaseSettings, validator
from typing import List, Optional
import re
import socket
import ipaddress
import urllib.parse

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "RSS Sentinel"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Bot Settings
    BOT_TOKEN: str
    ADMIN_IDS: str  # Comma-separated list of Telegram IDs
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/sentinel.db"
    
    # Web Server
    WEB_HOST: str = "0.0.0.0"
    WEB_PORT: int = 8000
    SECRET_KEY: str = "change-me-in-production"
    SESSION_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # RSS Settings
    CHECK_INTERVAL: int = 300  # seconds
    MAX_ENTRIES_PER_CHECK: int = 20
    USER_AGENT: str = "RSS Sentinel/1.0"
    REQUEST_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    
    # Filter Settings
    ENABLE_DUPLICATE_CHECK: bool = True
    DUPLICATE_HISTORY_DAYS: int = 7
    ENABLE_CONTENT_FILTER: bool = True
    DEFAULT_MIN_CONTENT_LENGTH: int = 50
    
    # Image Settings
    ENABLE_IMAGES: bool = True
    MAX_IMAGES_PER_POST: int = 4
    IMAGE_CACHE_DIR: str = "./data/media_cache"
    
    # Platform Settings
    TELEGRAM_CHANNEL_ID: Optional[str] = None
    VK_GROUP_ID: Optional[str] = None
    TWITTER_API_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @validator('BOT_TOKEN')
    def validate_bot_token(cls, v):
        if not v or len(v) < 40:
            raise ValueError("Invalid BOT_TOKEN format")
        return v.strip()
    
    @validator('ADMIN_IDS')
    def validate_admin_ids(cls, v):
        if not v:
            raise ValueError("ADMIN_IDS cannot be empty")
        try:
            ids = [int(x.strip()) for x in v.split(',')]
            if not ids:
                raise ValueError("At least one ADMIN_ID required")
        except ValueError:
            raise ValueError("ADMIN_IDS must be comma-separated integers")
        return v
    
    @validator('SECRET_KEY')
    def warn_secret_key(cls, v):
        if v == "change-me-in-production":
            import warnings
            warnings.warn("Using default SECRET_KEY! Change it in production.")
        return v
    
    @property
    def admin_id_list(self) -> List[int]:
        """Parse ADMIN_IDS into a list of integers"""
        return [int(x.strip()) for x in self.ADMIN_IDS.split(',')]
    
    @property
    def is_configured(self) -> bool:
        """Check if essential configuration is present"""
        return bool(self.BOT_TOKEN) and bool(self.ADMIN_IDS)


def is_valid_url(url: str) -> bool:
    """Validate URL and protect against SSRF attacks.
    Blocks private IP addresses and localhost."""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ['http', 'https']:
            return False
        
        hostname = parsed.hostname
        if not hostname:
            return False
        
        # Resolve hostname to IP addresses
        ip_addresses = socket.gethostbyname_ex(hostname)[2]
        
        for ip_str in ip_addresses:
            ip_obj = ipaddress.ip_address(ip_str)
            # Block private/internal IPs
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
                return False
        
        return True
    except Exception:
        return False


settings = Settings()
