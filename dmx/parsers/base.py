"""Base parser class and utilities."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union

from selectolax.parser import HTMLParser
from bs4 import BeautifulSoup

from dmx.utils.config import get_selectors
from dmx.utils.normalize import normalize_text


logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """Base class for all HTML parsers."""
    
    def __init__(self, selectors: Optional[Dict[str, Any]] = None):
        """Initialize parser with selectors."""
        self.selectors = selectors or get_selectors()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def parse_html(self, html_content: str, url: str) -> Dict[str, Any]:
        """Parse HTML content and extract data."""
        try:
            return self._parse_content(html_content, url)
        except Exception as e:
            self.logger.error(f"Failed to parse HTML from {url}: {e}")
            return {"error": str(e), "url": url}
    
    @abstractmethod
    def _parse_content(self, html_content: str, url: str) -> Dict[str, Any]:
        """Parse content - implemented by subclasses."""
        pass
    
    def _create_parser(self, html_content: str) -> HTMLParser:
        """Create selectolax parser."""
        return HTMLParser(html_content)
    
    def _create_soup(self, html_content: str) -> BeautifulSoup:
        """Create BeautifulSoup parser as fallback."""
        return BeautifulSoup(html_content, 'html.parser')
    
    def _extract_with_selectors(
        self, 
        parser: HTMLParser, 
        selectors: List[str], 
        attribute: Optional[str] = None,
        multiple: bool = False
    ) -> Union[str, List[str], None]:
        """Extract content using list of fallback selectors."""
        
        for selector in selectors:
            try:
                if multiple:
                    elements = parser.css(selector)
                    if elements:
                        if attribute:
                            return [elem.attributes.get(attribute, '') for elem in elements if elem.attributes.get(attribute)]
                        else:
                            return [normalize_text(elem.text()) for elem in elements if elem.text()]
                else:
                    element = parser.css_first(selector)
                    if element:
                        if attribute:
                            value = element.attributes.get(attribute)
                            return normalize_text(value) if value else None
                        else:
                            return normalize_text(element.text())
            except Exception as e:
                self.logger.debug(f"Selector '{selector}' failed: {e}")
                continue
        
        return [] if multiple else None
    
    def _extract_with_soup_selectors(
        self, 
        soup: BeautifulSoup, 
        selectors: List[str], 
        attribute: Optional[str] = None,
        multiple: bool = False
    ) -> Union[str, List[str], None]:
        """Extract content using BeautifulSoup as fallback."""
        
        for selector in selectors:
            try:
                if multiple:
                    elements = soup.select(selector)
                    if elements:
                        if attribute:
                            return [elem.get(attribute, '') for elem in elements if elem.get(attribute)]
                        else:
                            return [normalize_text(elem.get_text()) for elem in elements if elem.get_text()]
                else:
                    element = soup.select_one(selector)
                    if element:
                        if attribute:
                            value = element.get(attribute)
                            return normalize_text(value) if value else None
                        else:
                            return normalize_text(element.get_text())
            except Exception as e:
                self.logger.debug(f"Soup selector '{selector}' failed: {e}")
                continue
        
        return [] if multiple else None
    
    def _extract_links(self, parser: HTMLParser, selectors: List[str]) -> List[str]:
        """Extract links using selectors."""
        links = []
        
        for selector in selectors:
            try:
                elements = parser.css(selector)
                for element in elements:
                    href = element.attributes.get('href')
                    if href:
                        links.append(href)
            except Exception as e:
                self.logger.debug(f"Link selector '{selector}' failed: {e}")
                continue
        
        return links
    
    def _detect_page_type(self, parser: HTMLParser) -> str:
        """Detect page type based on content."""
        detection_selectors = self.selectors.get('page_detection', {})
        
        # Check for product detail page
        product_selectors = detection_selectors.get('is_product_detail', [])
        for selector in product_selectors:
            if parser.css_first(selector):
                return 'product_detail'
        
        # Check for category/listing page
        category_selectors = detection_selectors.get('is_category', [])
        for selector in category_selectors:
            if parser.css_first(selector):
                return 'category'
        
        # Check for homepage
        home_selectors = detection_selectors.get('is_homepage', [])
        for selector in home_selectors:
            if parser.css_first(selector):
                return 'home'
        
        return 'unknown'
    
    def _extract_meta_tags(self, parser: HTMLParser) -> Dict[str, str]:
        """Extract meta tags from HTML."""
        meta_data = {}
        
        # Title
        title_elem = parser.css_first('title')
        if title_elem:
            meta_data['title'] = normalize_text(title_elem.text())
        
        # Meta description
        desc_elem = parser.css_first('meta[name="description"]')
        if desc_elem:
            meta_data['description'] = normalize_text(desc_elem.attributes.get('content'))
        
        # OG tags
        og_title = parser.css_first('meta[property="og:title"]')
        if og_title:
            meta_data['og_title'] = normalize_text(og_title.attributes.get('content'))
        
        og_desc = parser.css_first('meta[property="og:description"]')
        if og_desc:
            meta_data['og_description'] = normalize_text(og_desc.attributes.get('content'))
        
        # Canonical URL
        canonical = parser.css_first('link[rel="canonical"]')
        if canonical:
            meta_data['canonical'] = canonical.attributes.get('href')
        
        return meta_data
    
    def _is_error_page(self, parser: HTMLParser) -> Optional[str]:
        """Check if page is an error page."""
        error_selectors = self.selectors.get('error_detection', {})
        
        for error_type, selectors in error_selectors.items():
            for selector in selectors:
                if parser.css_first(selector):
                    return error_type
        
        return None
    
    def _check_bot_detection(self, parser: HTMLParser) -> bool:
        """Check if page shows bot detection/captcha."""
        bot_selectors = self.selectors.get('bot_detection', {})
        
        for detection_type, selectors in bot_selectors.items():
            for selector in selectors:
                if parser.css_first(selector):
                    return True
        
        return False