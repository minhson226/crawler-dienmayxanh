# Add missing CategoryParser class 
"""
Category page parser
"""
import logging
from typing import List, Dict
from urllib.parse import urljoin
from .listing import ListingParser

logger = logging.getLogger(__name__)


class CategoryParser(ListingParser):
    """Parser for category pages - inherits from ListingParser"""
    
    def __init__(self):
        """Initialize category parser"""
        super().__init__()
    
    def extract_subcategories(self, html: str, base_url: str) -> List[Dict[str, str]]:
        """Extract subcategory links from category page"""
        # Implement subcategory extraction if needed
        return []