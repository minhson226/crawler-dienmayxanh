"""Home page parser for extracting category links."""

import re
from typing import Dict, Any, List
from urllib.parse import urljoin

from dmx.parsers.base import BaseParser
from dmx.utils.url import normalize_url, is_valid_url


class HomeParser(BaseParser):
    """Parser for homepage to extract category links."""
    
    def _parse_content(self, html_content: str, url: str) -> Dict[str, Any]:
        """Parse homepage content to extract category links."""
        parser = self._create_parser(html_content)
        
        # Check if this is actually a homepage
        if self._detect_page_type(parser) != 'home':
            self.logger.warning(f"URL {url} doesn't appear to be a homepage")
        
        # Check for errors
        error_type = self._is_error_page(parser)
        if error_type:
            return {"error": f"Error page detected: {error_type}", "url": url}
        
        # Check for bot detection
        if self._check_bot_detection(parser):
            return {"error": "Bot detection detected", "url": url}
        
        # Extract category links
        category_links = self._extract_category_links(parser, url)
        
        # Extract meta information
        meta_data = self._extract_meta_tags(parser)
        
        return {
            "url": url,
            "page_type": "home",
            "category_links": category_links,
            "meta": meta_data,
            "total_categories": len(category_links)
        }
    
    def _extract_category_links(self, parser, base_url: str) -> List[Dict[str, str]]:
        """Extract category links from homepage."""
        category_links = []
        seen_urls = set()
        
        # Get selectors for category links
        home_selectors = self.selectors.get('home', {})
        link_selectors = home_selectors.get('category_links', [])
        fallback_selectors = home_selectors.get('category_links_fallback', [])
        
        # Try main selectors first
        all_selectors = link_selectors + fallback_selectors
        
        for selector in all_selectors:
            try:
                elements = parser.css(selector)
                
                for element in elements:
                    href = element.attributes.get('href')
                    if not href:
                        continue
                    
                    # Make URL absolute
                    if not href.startswith(('http://', 'https://')):
                        href = urljoin(base_url, href)
                    
                    # Normalize URL
                    normalized_url = normalize_url(href)
                    
                    # Skip if already seen
                    if normalized_url in seen_urls:
                        continue
                    
                    # Validate URL
                    if not is_valid_url(normalized_url):
                        continue
                    
                    # Filter out non-category URLs
                    if not self._is_category_url(normalized_url):
                        continue
                    
                    # Extract category name
                    category_name = self._extract_category_name(element, normalized_url)
                    
                    if category_name:
                        category_links.append({
                            "name": category_name,
                            "url": normalized_url,
                            "source_selector": selector
                        })
                        seen_urls.add(normalized_url)
                        
            except Exception as e:
                self.logger.debug(f"Failed to extract links with selector '{selector}': {e}")
                continue
        
        # Sort by name for consistency
        category_links.sort(key=lambda x: x['name'])
        
        self.logger.info(f"Found {len(category_links)} category links")
        return category_links
    
    def _is_category_url(self, url: str) -> bool:
        """Check if URL looks like a category URL."""
        # Skip certain patterns that are definitely not categories
        skip_patterns = [
            r'/tin-tuc',
            r'/blog',
            r'/khuyen-mai(?!/[^/]+$)',  # Skip complex promo URLs but allow /khuyen-mai
            r'/gioi-thieu',
            r'/lien-he',
            r'/chinh-sach',
            r'/dieu-khoan',
            r'/sitemap',
            r'/search',
            r'/gio-hang',
            r'/thanh-toan',
            r'/dang-nhap',
            r'/dang-ky',
            r'\.php$',
            r'\.html$',
            r'\?.*',  # URLs with complex query params
        ]
        
        for pattern in skip_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        # Look for category patterns
        category_patterns = [
            r'/[a-z-]+/?$',              # Simple category like /may-lanh
            r'/[a-z-]+/[a-z-]+/?$',      # Subcategory like /may-lanh/may-lanh-panasonic
        ]
        
        for pattern in category_patterns:
            if re.search(pattern, url):
                return True
        
        return False
    
    def _extract_category_name(self, element, url: str) -> str:
        """Extract category name from link element."""
        # Try to get text from the element
        name = element.text()
        if name:
            name = name.strip()
            
            # Clean up common patterns
            name = re.sub(r'\s*\(\d+\)\s*$', '', name)  # Remove count like (123)
            name = re.sub(r'\s*>+\s*$', '', name)       # Remove trailing arrows
            name = re.sub(r'^\s*>+\s*', '', name)       # Remove leading arrows
            
            if name and len(name) > 2:
                return name
        
        # Fallback: extract from URL path
        try:
            path_parts = url.split('/')
            for part in reversed(path_parts):
                if part and part not in ['www.dienmayxanh.com', 'dienmayxanh.com']:
                    # Convert dash-separated to title case
                    name = part.replace('-', ' ').title()
                    if len(name) > 2:
                        return name
        except Exception:
            pass
        
        return "Unknown Category"
    
    def get_category_hierarchy(self, html_content: str, url: str) -> Dict[str, Any]:
        """Extract category hierarchy if available."""
        parser = self._create_parser(html_content)
        
        hierarchy = {}
        
        # Look for menu structures that might indicate hierarchy
        menu_selectors = [
            '.main-menu .submenu',
            '.category-menu .sub-menu',
            '.nav-menu .dropdown',
        ]
        
        for selector in menu_selectors:
            try:
                menu_elements = parser.css(selector)
                for menu_element in menu_elements:
                    # Extract parent category
                    parent_link = menu_element.parent.css_first('a')
                    if parent_link:
                        parent_name = parent_link.text().strip()
                        parent_url = parent_link.attributes.get('href')
                        
                        if parent_url:
                            parent_url = urljoin(url, parent_url)
                            
                            # Extract child categories
                            child_links = menu_element.css('a')
                            children = []
                            
                            for child_link in child_links:
                                child_name = child_link.text().strip()
                                child_url = child_link.attributes.get('href')
                                
                                if child_url and child_name:
                                    child_url = urljoin(url, child_url)
                                    children.append({
                                        "name": child_name,
                                        "url": normalize_url(child_url)
                                    })
                            
                            if children:
                                hierarchy[parent_name] = {
                                    "url": normalize_url(parent_url),
                                    "children": children
                                }
                        
            except Exception as e:
                self.logger.debug(f"Failed to extract hierarchy with selector '{selector}': {e}")
                continue
        
        return hierarchy