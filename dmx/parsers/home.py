"""
Home page parser to extract category links
"""
import logging
from typing import List, Dict, Any
from urllib.parse import urljoin, urlparse
from selectolax.parser import HTMLParser
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


class HomeParser:
    """Parser for home page to extract navigation and category links"""
    
    def __init__(self):
        """Initialize home parser with selectors"""
        self.selectors = self._load_selectors()
    
    def _load_selectors(self) -> Dict[str, Any]:
        """Load selectors from config file"""
        try:
            config_path = Path("configs/selectors.yaml")
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            else:
                # Fallback selectors
                return {
                    "home": {
                        "category_links": [
                            ".main-menu a[href]",
                            ".main-menu-header a[href]",
                            ".category a[href]",
                            "nav a[href*='/']"
                        ],
                        "navigation_menu": [
                            ".main-menu a",
                            ".main-menu-header a"
                        ]
                    }
                }
        except Exception as e:
            logger.error(f"Error loading selectors: {e}")
            return {}
    
    def extract_category_links(self, html: str, base_url: str) -> List[Dict[str, str]]:
        """Extract category links from home page"""
        try:
            parser = HTMLParser(html)
            category_links = []
            seen_urls = set()
            
            # Try each selector for category links
            selectors = self.selectors.get("home", {}).get("category_links", [])
            
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
                        
                        # Skip non-category URLs
                        if not self._is_category_url(full_url):
                            continue
                        
                        # Avoid duplicates
                        if full_url in seen_urls:
                            continue
                        seen_urls.add(full_url)
                        
                        # Extract category name
                        category_name = self._extract_category_name(link)
                        if not category_name:
                            continue
                        
                        category_links.append({
                            "name": category_name,
                            "url": full_url,
                            "selector_used": selector
                        })
                        
                        logger.debug(f"Found category: {category_name} -> {full_url}")
                        
                except Exception as e:
                    logger.warning(f"Error with selector '{selector}': {e}")
                    continue
            
            # Remove duplicates and filter valid categories
            unique_categories = []
            seen_names = set()
            
            for cat in category_links:
                if cat["name"] not in seen_names and len(cat["name"]) > 2:
                    unique_categories.append(cat)
                    seen_names.add(cat["name"])
            
            logger.info(f"Extracted {len(unique_categories)} unique categories")
            return unique_categories
            
        except Exception as e:
            logger.error(f"Error extracting category links: {e}")
            return []
    
    def _is_category_url(self, url: str) -> bool:
        """Check if URL looks like a category URL"""
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()
            
            # Skip non-category paths
            skip_patterns = [
                "javascript:",
                "mailto:",
                "tel:",
                "#",
                "/khuyen-mai",
                "/tin-tuc", 
                "/huong-dan",
                "/lien-he",
                "/gio-hang",
                "/thanh-toan",
                "/dang-nhap",
                "/dang-ky",
                "/flashsale",
                "/chuong-trinh",
                ".html",  # Specific product pages
                "utm_",   # UTM parameters
                "?g="     # Filter parameters
            ]
            
            for pattern in skip_patterns:
                if pattern in url.lower():
                    return False
            
            # Must have meaningful path
            if len(path) < 2 or path == "/":
                return False
            
            # Category URLs typically have format /category-name
            path_parts = [p for p in path.split("/") if p]
            if len(path_parts) == 1 and len(path_parts[0]) > 2:
                return True
            
            # Allow some 2-level categories
            if len(path_parts) == 2:
                return True
                
            return False
            
        except Exception:
            return False
    
    def _extract_category_name(self, link_element) -> str:
        """Extract category name from link element"""
        try:
            # Try text content first
            text = link_element.text(strip=True)
            if text and len(text) > 2:
                # Clean up the text
                text = text.replace("\n", " ").replace("\t", " ")
                text = " ".join(text.split())  # Normalize whitespace
                
                # Skip if it looks like navigation or utility text
                skip_texts = [
                    "danh mục",
                    "tất cả",
                    "xem thêm",
                    "more",
                    "menu",
                    "home",
                    "trang chủ"
                ]
                
                if text.lower() not in skip_texts:
                    return text
            
            # Try title attribute
            title = link_element.attributes.get("title")
            if title and len(title) > 2:
                return title.strip()
            
            # Try alt text of images
            img = link_element.css_first("img")
            if img:
                alt = img.attributes.get("alt")
                if alt and len(alt) > 2:
                    return alt.strip()
            
            return ""
            
        except Exception:
            return ""
    
    def extract_featured_products(self, html: str, base_url: str) -> List[Dict[str, str]]:
        """Extract featured products from home page"""
        try:
            parser = HTMLParser(html)
            products = []
            
            # Look for featured product sections
            featured_selectors = [
                ".featured-products a[href]",
                ".hot-products a[href]",
                ".sale-products a[href]",
                ".owl-carousel .item a[href]"
            ]
            
            for selector in featured_selectors:
                try:
                    links = parser.css(selector)
                    for link in links:
                        href = link.attributes.get("href")
                        if not href:
                            continue
                        
                        if href.startswith("/"):
                            full_url = urljoin(base_url, href)
                        elif href.startswith("http"):
                            full_url = href
                        else:
                            continue
                        
                        # Must look like product URL
                        if self._is_product_url(full_url):
                            name = link.text(strip=True) or "Featured Product"
                            products.append({
                                "name": name,
                                "url": full_url
                            })
                            
                except Exception as e:
                    logger.warning(f"Error with featured selector '{selector}': {e}")
            
            return products
            
        except Exception as e:
            logger.error(f"Error extracting featured products: {e}")
            return []
    
    def _is_product_url(self, url: str) -> bool:
        """Check if URL looks like a product URL"""
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()
            
            # Product URLs typically have more path segments or specific patterns
            if path.count("/") >= 2:
                return True
            
            # Check for product-like patterns
            product_patterns = [
                ".html",
                "sp",
                "product",
                "item"
            ]
            
            for pattern in product_patterns:
                if pattern in path:
                    return True
            
            return False
            
        except Exception:
            return False