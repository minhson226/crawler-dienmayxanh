"""Category page parser for extracting product links and pagination."""

import re
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin

from dmx.parsers.base import BaseParser
from dmx.utils.url import normalize_url, is_valid_url
from dmx.utils.normalize import normalize_text


class CategoryParser(BaseParser):
    """Parser for category pages to extract product links and pagination."""
    
    def _parse_content(self, html_content: str, url: str) -> Dict[str, Any]:
        """Parse category page content."""
        parser = self._create_parser(html_content)
        
        # Check if this is actually a category page
        if self._detect_page_type(parser) not in ['category', 'listing']:
            self.logger.warning(f"URL {url} doesn't appear to be a category page")
        
        # Check for errors
        error_type = self._is_error_page(parser)
        if error_type:
            return {"error": f"Error page detected: {error_type}", "url": url}
        
        # Check for bot detection
        if self._check_bot_detection(parser):
            return {"error": "Bot detection detected", "url": url}
        
        # Extract breadcrumb for category path
        breadcrumb = self._extract_breadcrumb(parser)
        
        # Extract product links
        product_links = self._extract_product_links(parser, url)
        
        # Extract pagination info
        pagination = self._extract_pagination(parser, url)
        
        # Extract category info
        category_info = self._extract_category_info(parser)
        
        # Extract meta information
        meta_data = self._extract_meta_tags(parser)
        
        return {
            "url": url,
            "page_type": "category",
            "breadcrumb": breadcrumb,
            "category_info": category_info,
            "product_links": product_links,
            "pagination": pagination,
            "meta": meta_data,
            "total_products": len(product_links)
        }
    
    def _extract_breadcrumb(self, parser) -> Optional[str]:
        """Extract breadcrumb navigation."""
        category_selectors = self.selectors.get('category', {})
        breadcrumb_selectors = category_selectors.get('breadcrumb', [])
        
        # Try to extract breadcrumb text
        breadcrumb_text = self._extract_with_selectors(parser, breadcrumb_selectors)
        
        if breadcrumb_text:
            # Clean up breadcrumb text
            breadcrumb_text = re.sub(r'\s+', ' ', breadcrumb_text)
            breadcrumb_text = re.sub(r'\s*>\s*', ' > ', breadcrumb_text)
            return breadcrumb_text.strip()
        
        return None
    
    def _extract_product_links(self, parser, base_url: str) -> List[Dict[str, Any]]:
        """Extract product links from category page."""
        product_links = []
        seen_urls = set()
        
        category_selectors = self.selectors.get('category', {})
        link_selectors = category_selectors.get('product_card_links', [])
        
        for selector in link_selectors:
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
                    
                    # Check if it looks like a product URL
                    if not self._is_product_url(normalized_url):
                        continue
                    
                    # Extract product info from the card
                    product_info = self._extract_product_card_info(element, parser)
                    
                    product_data = {
                        "url": normalized_url,
                        "source_selector": selector,
                        **product_info
                    }
                    
                    product_links.append(product_data)
                    seen_urls.add(normalized_url)
                    
            except Exception as e:
                self.logger.debug(f"Failed to extract product links with selector '{selector}': {e}")
                continue
        
        self.logger.info(f"Found {len(product_links)} product links")
        return product_links
    
    def _extract_product_card_info(self, link_element, parser) -> Dict[str, Any]:
        """Extract basic product info from product card."""
        product_info = {}
        
        # Try to find the product card container
        card_element = link_element
        
        # Look for parent elements that might be the card
        current = link_element
        for _ in range(3):  # Check up to 3 levels up
            if current.parent:
                current = current.parent
                # Check if this looks like a product card
                class_name = current.attributes.get('class', '')
                if any(term in class_name.lower() for term in ['item', 'product', 'card']):
                    card_element = current
                    break
        
        category_selectors = self.selectors.get('category', {})
        card_info_selectors = category_selectors.get('product_card_info', {})
        
        # Extract name
        name_selectors = card_info_selectors.get('name', [])
        if name_selectors:
            for selector in name_selectors:
                name_elem = card_element.css_first(selector)
                if name_elem:
                    product_info['name'] = normalize_text(name_elem.text())
                    break
        
        # Extract price
        price_selectors = card_info_selectors.get('price', [])
        if price_selectors:
            for selector in price_selectors:
                price_elem = card_element.css_first(selector)
                if price_elem:
                    product_info['price_text'] = normalize_text(price_elem.text())
                    break
        
        # Extract image
        image_selectors = card_info_selectors.get('image', [])
        if image_selectors:
            for selector in image_selectors:
                image_elem = card_element.css_first(selector)
                if image_elem:
                    image_src = image_elem.attributes.get('src') or image_elem.attributes.get('data-src')
                    if image_src:
                        product_info['image_url'] = image_src
                        break
        
        return product_info
    
    def _extract_pagination(self, parser, base_url: str) -> Dict[str, Any]:
        """Extract pagination information."""
        pagination_info = {
            "current_page": 1,
            "total_pages": None,
            "next_page_url": None,
            "page_urls": []
        }
        
        category_selectors = self.selectors.get('category', {})
        pagination_selectors = category_selectors.get('pagination', {})
        
        # Extract next page URL
        next_page_selectors = pagination_selectors.get('next_page', [])
        for selector in next_page_selectors:
            try:
                next_elem = parser.css_first(selector)
                if next_elem:
                    next_href = next_elem.attributes.get('href')
                    if next_href:
                        if not next_href.startswith(('http://', 'https://')):
                            next_href = urljoin(base_url, next_href)
                        pagination_info['next_page_url'] = normalize_url(next_href)
                        break
            except Exception as e:
                self.logger.debug(f"Failed to extract next page with selector '{selector}': {e}")
                continue
        
        # Extract page numbers
        page_number_selectors = pagination_selectors.get('page_numbers', [])
        for selector in page_number_selectors:
            try:
                page_elements = parser.css(selector)
                page_urls = []
                
                for page_elem in page_elements:
                    page_href = page_elem.attributes.get('href')
                    page_text = normalize_text(page_elem.text())
                    
                    if page_href and page_text:
                        if not page_href.startswith(('http://', 'https://')):
                            page_href = urljoin(base_url, page_href)
                        
                        # Try to extract page number
                        page_num = None
                        if page_text.isdigit():
                            page_num = int(page_text)
                        
                        page_urls.append({
                            "page": page_num,
                            "url": normalize_url(page_href),
                            "text": page_text
                        })
                
                if page_urls:
                    pagination_info['page_urls'] = page_urls
                    
                    # Determine current page and total pages
                    page_numbers = [p['page'] for p in page_urls if p['page'] is not None]
                    if page_numbers:
                        pagination_info['total_pages'] = max(page_numbers)
                    
                    break
                    
            except Exception as e:
                self.logger.debug(f"Failed to extract page numbers with selector '{selector}': {e}")
                continue
        
        return pagination_info
    
    def _extract_category_info(self, parser) -> Dict[str, Any]:
        """Extract category-specific information."""
        category_info = {}
        
        # Extract category title/name
        title_selectors = ['h1', '.category-title', '.page-title', 'title']
        for selector in title_selectors:
            try:
                title_elem = parser.css_first(selector)
                if title_elem:
                    title_text = normalize_text(title_elem.text())
                    if title_text and 'điện máy xanh' not in title_text.lower():
                        category_info['title'] = title_text
                        break
            except Exception:
                continue
        
        # Extract category description if available
        desc_selectors = ['.category-description', '.category-intro', '.page-description']
        for selector in desc_selectors:
            try:
                desc_elem = parser.css_first(selector)
                if desc_elem:
                    desc_text = normalize_text(desc_elem.text())
                    if desc_text and len(desc_text) > 20:
                        category_info['description'] = desc_text
                        break
            except Exception:
                continue
        
        # Extract product count if displayed
        count_selectors = ['.product-count', '.result-count', '.total-products']
        for selector in count_selectors:
            try:
                count_elem = parser.css_first(selector)
                if count_elem:
                    count_text = normalize_text(count_elem.text())
                    # Try to extract number from text like "Showing 20 of 150 products"
                    count_match = re.search(r'(\d+)', count_text)
                    if count_match:
                        category_info['product_count'] = int(count_match.group(1))
                        break
            except Exception:
                continue
        
        return category_info
    
    def _is_product_url(self, url: str) -> bool:
        """Check if URL looks like a product URL."""
        # Product URLs typically have this pattern:
        # /category/product-name-with-model-123
        
        # Skip certain patterns that are definitely not products
        skip_patterns = [
            r'/c=',           # Category filters
            r'/p=',           # Pagination
            r'/filter',       # Filters
            r'/sort',         # Sorting
            r'/page',         # Page numbers
            r'\?.*',          # Complex query params
        ]
        
        for pattern in skip_patterns:
            if re.search(pattern, url):
                return False
        
        # Look for product patterns
        product_patterns = [
            r'/[^/]+/[^/]+-[a-z0-9]+/?$',     # /category/product-name-code
            r'/[^/]+/[^/]+-\d+/?$',           # /category/product-name-123
        ]
        
        for pattern in product_patterns:
            if re.search(pattern, url):
                return True
        
        return False