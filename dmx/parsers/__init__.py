"""Parsers package initialization."""

from dmx.parsers.base import BaseParser
from dmx.parsers.home import HomeParser
from dmx.parsers.category import CategoryParser
from dmx.parsers.product_detail import ProductDetailParser

__all__ = [
    "BaseParser",
    "HomeParser", 
    "CategoryParser",
    "ProductDetailParser",
]


def get_parser_for_page_type(page_type: str) -> BaseParser:
    """Get appropriate parser for page type."""
    parser_map = {
        'home': HomeParser,
        'category': CategoryParser,
        'product_detail': ProductDetailParser,
        'listing': CategoryParser,  # Use category parser for listing pages
    }
    
    parser_class = parser_map.get(page_type, BaseParser)
    return parser_class()


def detect_and_parse(html_content: str, url: str) -> dict:
    """Auto-detect page type and parse with appropriate parser."""
    # Try to detect page type using base parser
    base_parser = BaseParser()
    parser_instance = base_parser._create_parser(html_content)
    page_type = base_parser._detect_page_type(parser_instance)
    
    # Get appropriate parser and parse content
    parser = get_parser_for_page_type(page_type)
    return parser.parse_html(html_content, url)