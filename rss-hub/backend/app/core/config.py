"""
RSS Hub Configuration Module
Handles environment variables, validation, and SSRF protection.
"""
import os
import re
import socket
import struct
from urllib.parse import urlparse
from typing import Optional, List
from dataclasses import dataclass, field


@dataclass
class DatabaseConfig:
    path: str = "data/rss_hub.db"
    pool_size: int = 5
    timeout: int = 30
    wal_mode: bool = True


@dataclass
class BotConfig:
    token: str = ""
    admin_ids: List[int] = field(default_factory=list)
    channel_id: Optional[str] = None
    check_interval: int = 300  # 5 minutes
    max_retries: int = 3
    retry_delay: int = 60


@dataclass
class WebConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    secret_key: str = ""
    cors_origins: List[str] = field(default_factory=lambda: ["http://localhost:3000"])
    debug: bool = False


@dataclass
class RSSConfig:
    user_agent: str = "RSSHub/1.0"
    timeout: int = 10
    max_entries_per_feed: int = 50
    allowed_tags: List[str] = field(default_factory=lambda: [
        'b', 'i', 'u', 'strong', 'em', 'a', 'p', 'br', 'ul', 'ol', 'li', 'img'
    ])
    blocked_tags: List[str] = field(default_factory=lambda: [
        'script', 'iframe', 'object', 'embed', 'form', 'input', 'style'
    ])


@dataclass
class AppConfig:
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    bot: BotConfig = field(default_factory=BotConfig)
    web: WebConfig = field(default_factory=WebConfig)
    rss: RSSConfig = field(default_factory=RSSConfig)
    log_level: str = "INFO"
    environment: str = "production"


def is_valid_url(url: str) -> bool:
    """Validate URL and protect against SSRF attacks."""
    try:
        parsed = urlparse(url)
        
        if parsed.scheme not in ['http', 'https']:
            return False
        
        hostname = parsed.hostname
        if not hostname:
            return False
        
        # Check for internal IP addresses
        ip_addresses = socket.gethostbyname_ex(hostname)[2]
        
        for ip in ip_addresses:
            if is_internal_ip(ip):
                return False
        
        return True
    except Exception:
        return False


def is_internal_ip(ip: str) -> bool:
    """Check if IP address is internal/private."""
    try:
        ip_bytes = socket.inet_aton(ip)
        ip_int = struct.unpack("!I", ip_bytes)[0]
        
        # Private IP ranges
        private_ranges = [
            (0x0A000000, 0x0AFFFFFF),      # 10.0.0.0/8
            (0xAC100000, 0xAC1FFFFF),      # 172.16.0.0/12
            (0xC0A80000, 0xC0A8FFFF),      # 192.168.0.0/16
            (0x7F000000, 0x7FFFFFFF),      # 127.0.0.0/8
            (0x00000000, 0x00FFFFFF),      # 0.0.0.0/8
            (0xA9FE0000, 0xA9FEFFFF),      # 169.254.0.0/16
        ]
        
        return any(start <= ip_int <= end for start, end in private_ranges)
    except Exception:
        return True  # Assume internal if we can't check


def sanitize_token(token: str) -> str:
    """Remove whitespace and validate bot token format."""
    cleaned = token.strip()
    if not re.match(r'^\d+:[\w-]+$', cleaned):
        raise ValueError("Invalid bot token format")
    return cleaned


def parse_admin_ids(admin_ids_str: str) -> List[int]:
    """Parse comma-separated admin IDs."""
    if not admin_ids_str:
        return []
    
    try:
        return [int(x.strip()) for x in admin_ids_str.split(',') if x.strip()]
    except ValueError:
        raise ValueError("Admin IDs must be comma-separated integers")


def load_config() -> AppConfig:
    """Load configuration from environment variables."""
    # Database
    db_path = os.getenv('DATABASE_PATH', 'data/rss_hub.db')
    
    # Bot
    bot_token = sanitize_token(os.getenv('BOT_TOKEN', ''))
    admin_ids = parse_admin_ids(os.getenv('ADMIN_IDS', ''))
    channel_id = os.getenv('CHANNEL_ID')
    check_interval = int(os.getenv('CHECK_INTERVAL', '300'))
    
    # Web
    web_host = os.getenv('WEB_HOST', '0.0.0.0')
    web_port = int(os.getenv('WEB_PORT', '8000'))
    secret_key = os.getenv('SECRET_KEY', '')
    if not secret_key:
        secret_key = os.urandom(32).hex()
    
    # RSS
    user_agent = os.getenv('RSS_USER_AGENT', 'RSSHub/1.0')
    rss_timeout = int(os.getenv('RSS_TIMEOUT', '10'))
    
    config = AppConfig(
        database=DatabaseConfig(path=db_path),
        bot=BotConfig(
            token=bot_token,
            admin_ids=admin_ids,
            channel_id=channel_id,
            check_interval=check_interval
        ),
        web=WebConfig(
            host=web_host,
            port=web_port,
            secret_key=secret_key,
            debug=os.getenv('DEBUG', 'false').lower() == 'true'
        ),
        rss=RSSConfig(
            user_agent=user_agent,
            timeout=rss_timeout
        ),
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        environment=os.getenv('ENVIRONMENT', 'production')
    )
    
    # Validate required fields
    if not config.bot.token:
        raise ValueError("BOT_TOKEN is required")
    if not config.bot.admin_ids:
        raise ValueError("ADMIN_IDS is required")
    
    return config


# Global config instance
config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get global config instance."""
    global config
    if config is None:
        config = load_config()
    return config
