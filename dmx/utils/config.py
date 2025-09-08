"""Configuration management utilities."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    concurrency: int = 3
    delay_range: list = field(default_factory=lambda: [1, 3])
    max_requests_per_minute: int = 20
    backoff_factor: float = 2.0
    max_retries: int = 3


@dataclass 
class RobotsConfig:
    """Robots.txt configuration."""
    respect: bool = True
    crawl_delay_override: Optional[int] = None
    check_interval: int = 3600


@dataclass
class BrowserConfig:
    """Browser configuration."""
    use_playwright: str = "auto"  # auto, static, always
    headless: bool = True
    timeout: int = 30000
    viewport: dict = field(default_factory=lambda: {"width": 1920, "height": 1080})


@dataclass
class LimitsConfig:
    """Crawler limits configuration."""
    max_products: int = 1000
    max_categories: int = 50
    max_pages_per_category: int = 20
    category_levels: int = 3


@dataclass
class PatternsConfig:
    """URL patterns configuration."""
    include: list = field(default_factory=list)
    exclude: list = field(default_factory=list)


@dataclass
class StorageConfig:
    """Storage configuration."""
    save_raw_html: bool = False
    save_images_locally: bool = False
    deduplicate_by: str = "canonical_url"
    update_existing: bool = True


@dataclass
class CacheConfig:
    """Cache configuration."""
    enabled: bool = True
    expire_after: int = 3600
    backend: str = "sqlite"


@dataclass
class Config:
    """Main configuration class."""
    base_url: str = "https://www.dienmayxanh.com"
    user_agent: str = "DMX-Crawler/1.0 (Educational Purpose)"
    
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    robots: RobotsConfig = field(default_factory=RobotsConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    limits: LimitsConfig = field(default_factory=LimitsConfig)
    patterns: PatternsConfig = field(default_factory=PatternsConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)


# Global config instance
_config: Optional[Config] = None


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from YAML file."""
    global _config
    
    if config_path is None:
        # Look for config file in standard locations
        possible_paths = [
            "configs/config.yaml",
            "config.yaml",
            os.path.expanduser("~/.dmx/config.yaml"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                config_path = path
                break
    
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # Create config from loaded data
        _config = Config(
            base_url=config_data.get("base_url", "https://www.dienmayxanh.com"),
            user_agent=config_data.get("user_agent", "DMX-Crawler/1.0"),
            
            rate_limit=RateLimitConfig(**config_data.get("rate_limit", {})),
            robots=RobotsConfig(**config_data.get("robots", {})),
            browser=BrowserConfig(**config_data.get("browser", {})),
            limits=LimitsConfig(**config_data.get("limits", {})),
            patterns=PatternsConfig(**config_data.get("patterns", {})),
            storage=StorageConfig(**config_data.get("storage", {})),
            cache=CacheConfig(**config_data.get("cache", {})),
        )
    else:
        # Use default config
        _config = Config()
    
    return _config


def get_config() -> Config:
    """Get current configuration."""
    global _config
    
    if _config is None:
        _config = load_config()
    
    return _config


def reload_config(config_path: Optional[str] = None) -> Config:
    """Reload configuration from file."""
    global _config
    _config = None
    return load_config(config_path)


def get_selectors() -> Dict[str, Any]:
    """Load selectors configuration."""
    possible_paths = [
        "configs/selectors.yaml",
        "selectors.yaml",
        os.path.expanduser("~/.dmx/selectors.yaml"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
    
    # Return empty dict if no selectors file found
    return {}


def validate_config(config: Config) -> list:
    """Validate configuration and return list of errors."""
    errors = []
    
    # Validate base URL
    if not config.base_url or not config.base_url.startswith(('http://', 'https://')):
        errors.append("base_url must be a valid HTTP/HTTPS URL")
    
    # Validate rate limiting
    if config.rate_limit.concurrency < 1:
        errors.append("rate_limit.concurrency must be >= 1")
    
    if config.rate_limit.max_requests_per_minute < 1:
        errors.append("rate_limit.max_requests_per_minute must be >= 1")
    
    # Validate limits
    if config.limits.max_products < 1:
        errors.append("limits.max_products must be >= 1")
    
    if config.limits.max_categories < 1:
        errors.append("limits.max_categories must be >= 1")
    
    # Validate browser config
    if config.browser.use_playwright not in ['auto', 'static', 'always']:
        errors.append("browser.use_playwright must be 'auto', 'static', or 'always'")
    
    if config.browser.timeout < 1000:
        errors.append("browser.timeout must be >= 1000 milliseconds")
    
    return errors