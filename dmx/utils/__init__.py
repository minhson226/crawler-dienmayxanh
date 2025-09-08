"""Utils package initialization."""

from dmx.utils.config import get_config, load_config, get_selectors
from dmx.utils.url import normalize_url, clean_query_params, is_valid_url
from dmx.utils.normalize import normalize_text, normalize_price, normalize_product_name
from dmx.utils.export import export_products, export_categories

__all__ = [
    # Config
    "get_config",
    "load_config", 
    "get_selectors",
    # URL utilities
    "normalize_url",
    "clean_query_params",
    "is_valid_url",
    # Text normalization
    "normalize_text",
    "normalize_price",
    "normalize_product_name",
    # Export
    "export_products",
    "export_categories",
]