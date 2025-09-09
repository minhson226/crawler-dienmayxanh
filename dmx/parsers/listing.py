"""
Listing page parser to extract product links and pagination
"""
import logging
from typing import List, Optional
from urllib.parse import urljoin, urlparse
from selectolax.parser import HTMLParser
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


class ListingParser:
    """Parser for product listing pages"""
    
    def __init__(self):
        """Initialize listing parser with selectors"""
        self.selectors = self._load_selectors()
    
    def _load_selectors(self) -> dict:
        """Load selectors from config file"""
        try:
            config_path = Path("configs/selectors.yaml")
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            else:
                # Fallback selectors
                return {
                    "category": {
                        "product_links": [
                            ".listproduct .item a[href]",
                            ".product-item a[href]",
                            ".item-img a[href]",
                            "h3 a[href]"
                        ],
                        "next_page": [
                            "a.next",
                            "a[rel='next']", 
                            ".pagination .next",
                            ".paging a.next"
                        ]
                    }
                }
        except Exception as e:
            logger.error(f"Error loading selectors: {e}")
            return {}
    
    def extract_product_links(self, html: str, base_url: str) -> List[str]:
        """Extract product page links from listing page"""
        try:
            parser = HTMLParser(html)
            product_links = []
            seen_urls = set()
            
            # Try each selector for product links
            selectors = self.selectors.get("category", {}).get("product_links", [])
            
            for selector in selectors:
                try:
                    links = parser.css(selector)
                    for link in links:
                        href = link.attributes.get("href")
                        if not href:
                            continue
                        
                        # Build absolute URL
                        if href.startswith("/"):
                            full_url = urljoin(base_url, href)
                        elif href.startswith("http"):
                            full_url = href
                        else:
                            continue
                        
                        # Skip non-product URLs
                        if not self._is_product_url(full_url):
                            continue
                        
                        # Avoid duplicates
                        if full_url in seen_urls:
                            continue
                        seen_urls.add(full_url)
                        
                        product_links.append(full_url)
                        logger.debug(f"Found product link: {full_url}")
                        
                except Exception as e:
                    logger.warning(f"Error with selector '{selector}': {e}")
                    continue
            
            logger.info(f"Extracted {len(product_links)} product links")
            return product_links
            
        except Exception as e:
            logger.error(f"Error extracting product links: {e}")
            return []
    
    def has_next_page(self, html: str) -> bool:
        """Check if there is a next page"""
        try:
            parser = HTMLParser(html)
            
            # Try each selector for next page
            selectors = self.selectors.get("category", {}).get("next_page", [])
            
            for selector in selectors:
                try:
                    next_link = parser.css_first(selector)
                    if next_link:
                        href = next_link.attributes.get("href")
                        if href and href != "#":
                            logger.debug(f"Found next page with selector: {selector}")
                            return True
                except Exception:
                    continue
            
            # Check for numbered pagination
            pagination_numbers = parser.css(".pagination a, .paging a")
            current_page = None
            max_page = 0
            
            for link in pagination_numbers:
                text = link.text(strip=True)
                if text.isdigit():
                    page_num = int(text)
                    max_page = max(max_page, page_num)
                    
                    # Check if this is the current page
                    if "active" in link.attributes.get("class", ""):
                        current_page = page_num
            
            if current_page and current_page < max_page:
                logger.debug(f"Found next page via pagination: {current_page} < {max_page}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking next page: {e}")
            return False
    
    def get_next_page_url(self, html: str, base_url: str) -> Optional[str]:
        """Get the URL of the next page"""
        try:
            parser = HTMLParser(html)
            
            # Try each selector for next page
            selectors = self.selectors.get("category", {}).get("next_page", [])
            
            for selector in selectors:
                try:
                    next_link = parser.css_first(selector)
                    if next_link:
                        href = next_link.attributes.get("href")
                        if href and href != "#":
                            if href.startswith("/"):
                                return urljoin(base_url, href)
                            elif href.startswith("http"):
                                return href
                except Exception:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting next page URL: {e}")
            return None
    
    def extract_breadcrumb(self, html: str) -> List[str]:
        """Extract breadcrumb navigation"""
        try:
            parser = HTMLParser(html)
            breadcrumb = []
            
            # Try breadcrumb selectors
            selectors = self.selectors.get("category", {}).get("breadcrumb", [])
            
            for selector in selectors:
                try:
                    breadcrumb_container = parser.css_first(selector)
                    if breadcrumb_container:
                        # Extract breadcrumb items
                        items = breadcrumb_container.css("li, a, span")
                        for item in items:
                            text = item.text(strip=True)
                            if text and text not in ["Home", "Trang chủ", ">"]:
                                breadcrumb.append(text)
                        
                        if breadcrumb:
                            break
                            
                except Exception:
                    continue
            
            return breadcrumb
            
        except Exception as e:
            logger.error(f"Error extracting breadcrumb: {e}")
            return []
    
    def extract_category_info(self, html: str) -> dict:
        """Extract category information from listing page"""
        try:
            parser = HTMLParser(html)
            
            # Extract category title
            title_selectors = ["h1", ".category-title", ".page-title", "title"]
            category_title = ""
            
            for selector in title_selectors:
                element = parser.css_first(selector)
                if element:
                    text = element.text(strip=True)
                    if text and len(text) > 2:
                        category_title = text
                        break
            
            # Extract product count if available
            count_selectors = [".product-count", ".results-count", ".total-items"]
            product_count = None
            
            for selector in count_selectors:
                element = parser.css_first(selector)
                if element:
                    text = element.text(strip=True)
                    # Try to extract number from text
                    import re
                    numbers = re.findall(r'\d+', text)
                    if numbers:
                        product_count = int(numbers[0])
                        break
            
            # Extract breadcrumb
            breadcrumb = self.extract_breadcrumb(html)
            
            return {
                "title": category_title,
                "product_count": product_count,
                "breadcrumb": breadcrumb
            }
            
        except Exception as e:
            logger.error(f"Error extracting category info: {e}")
            return {}
    
    def _is_product_url(self, url: str) -> bool:
        """Check if URL looks like a product URL"""
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()
            
            # Skip non-product patterns
            skip_patterns = [
                "/khuyen-mai",
                "/tin-tuc",
                "/chuong-trinh",
                "/bang-gia",
                "/lien-he",
                "/huong-dan",
                "javascript:",
                "mailto:",
                "tel:"
            ]
            
            for pattern in skip_patterns:
                if pattern in url.lower():
                    return False
            
            # Product URLs typically have specific patterns
            # In dienmayxanh.com, products usually have paths like:
            # /may-lanh/may-lanh-toshiba-1-hp-h10qksg-v
            # /tivi/smart-tivi-samsung-43-inch-ua43t6500
            
            path_parts = [p for p in path.split("/") if p]
            
            # Must have at least 2 path segments (category/product)
            if len(path_parts) >= 2:
                return True
            
            # Check for product-like extensions
            if path.endswith('.html') or 'sp' in path:
                return True
            
            return False
            
        except Exception:
            return False