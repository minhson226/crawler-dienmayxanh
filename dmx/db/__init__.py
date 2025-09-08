"""Database package initialization."""

from dmx.db.models import (
    Base,
    Product,
    Category,
    ProductSpec,
    ProductImage,
    ProductVariant,
    CrawlSession,
    CrawlError,
    StoreAvailability,
    PriceHistory,
)
from dmx.db.session import (
    init_db,
    get_session,
    create_session,
    get_engine,
    health_check,
    get_db_info,
)

__all__ = [
    # Models
    "Base",
    "Product",
    "Category", 
    "ProductSpec",
    "ProductImage",
    "ProductVariant",
    "CrawlSession",
    "CrawlError",
    "StoreAvailability",
    "PriceHistory",
    # Session management
    "init_db",
    "get_session",
    "create_session",
    "get_engine",
    "health_check",
    "get_db_info",
]