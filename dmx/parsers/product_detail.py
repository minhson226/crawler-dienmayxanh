"""Product detail page parser for extracting comprehensive product information."""

import re
import json
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin

from dmx.parsers.base import BaseParser
from dmx.utils.url import normalize_url
from dmx.utils.normalize import (
    normalize_text, normalize_price, normalize_discount_percent,
    normalize_rating, normalize_warranty, normalize_availability,
    normalize_brand, normalize_model, normalize_category_path,
    normalize_spec_key, normalize_spec_value, normalize_product_name
)


class ProductDetailParser(BaseParser):
    """Parser for product detail pages."""
    
    def _parse_content(self, html_content: str, url: str) -> Dict[str, Any]:
        """Parse product detail page content."""
        parser = self._create_parser(html_content)
        
        # Check if this is actually a product detail page
        if self._detect_page_type(parser) != 'product_detail':
            self.logger.warning(f"URL {url} doesn't appear to be a product detail page")
        
        # Check for errors
        error_type = self._is_error_page(parser)
        if error_type:
            return {"error": f"Error page detected: {error_type}", "url": url}
        
        # Check for bot detection
        if self._check_bot_detection(parser):
            return {"error": "Bot detection detected", "url": url}
        
        # Extract all product information
        product_data = {
            "url": url,
            "page_type": "product_detail",
        }
        
        # Basic product info
        product_data.update(self._extract_basic_info(parser))
        
        # Pricing information
        product_data.update(self._extract_pricing(parser))
        
        # Product specifications
        product_data["specifications"] = self._extract_specifications(parser)
        
        # Images
        product_data["images"] = self._extract_images(parser, url)
        
        # Descriptions
        product_data.update(self._extract_descriptions(parser))
        
        # Availability and logistics
        product_data.update(self._extract_availability_info(parser))
        
        # Ratings and reviews
        product_data.update(self._extract_ratings(parser))
        
        # Meta and SEO
        product_data["meta"] = self._extract_meta_tags(parser)
        
        # Category path
        product_data["category_path"] = self._extract_category_path(parser)
        
        # Structured data (JSON-LD)
        structured_data = self._extract_structured_data(parser)
        if structured_data:
            product_data["structured_data"] = structured_data
        
        return product_data
    
    def _extract_basic_info(self, parser) -> Dict[str, Any]:
        """Extract basic product information."""
        detail_selectors = self.selectors.get('product_detail', {})
        
        basic_info = {}
        
        # Product name
        name_selectors = detail_selectors.get('name', [])
        name = self._extract_with_selectors(parser, name_selectors)
        if name:
            basic_info['name'] = normalize_product_name(name)
        
        # Brand
        brand_selectors = detail_selectors.get('brand', [])
        brand = self._extract_with_selectors(parser, brand_selectors)
        if brand:
            basic_info['brand'] = normalize_brand(brand)
        
        # Model
        model_selectors = detail_selectors.get('model', [])
        model = self._extract_with_selectors(parser, model_selectors)
        if model:
            basic_info['model'] = normalize_model(model)
        
        # SKU/Product Code
        sku_selectors = detail_selectors.get('sku', [])
        sku = self._extract_with_selectors(parser, sku_selectors)
        if sku:
            basic_info['product_code'] = normalize_text(sku)
        
        return basic_info
    
    def _extract_pricing(self, parser) -> Dict[str, Any]:
        """Extract pricing information."""
        detail_selectors = self.selectors.get('product_detail', {})
        
        pricing = {}
        
        # Current/promotional price
        current_price_selectors = detail_selectors.get('price_current', [])
        current_price_text = self._extract_with_selectors(parser, current_price_selectors)
        if current_price_text:
            pricing['price_promo'] = normalize_price(current_price_text)
            pricing['price_promo_text'] = current_price_text
        
        # Original price
        original_price_selectors = detail_selectors.get('price_original', [])
        original_price_text = self._extract_with_selectors(parser, original_price_selectors)
        if original_price_text:
            pricing['price_regular'] = normalize_price(original_price_text)
            pricing['price_regular_text'] = original_price_text
        
        # Discount percentage
        discount_selectors = detail_selectors.get('discount_percent', [])
        discount_text = self._extract_with_selectors(parser, discount_selectors)
        if discount_text:
            pricing['discount_percent'] = normalize_discount_percent(discount_text)
            pricing['discount_text'] = discount_text
        
        return pricing
    
    def _extract_specifications(self, parser) -> List[Dict[str, Any]]:
        """Extract product specifications."""
        detail_selectors = self.selectors.get('product_detail', {})
        specifications = []
        
        # Try different specification extraction methods
        specs_container_selectors = detail_selectors.get('specs_container', [])
        specs_items_selectors = detail_selectors.get('specs_items', [])
        
        # Method 1: Look for specification containers
        for container_selector in specs_container_selectors:
            try:
                container = parser.css_first(container_selector)
                if container:
                    specs = self._extract_specs_from_container(container, detail_selectors)
                    if specs:
                        specifications.extend(specs)
                        break
            except Exception as e:
                self.logger.debug(f"Failed to extract specs from container '{container_selector}': {e}")
                continue
        
        # Method 2: Look for individual spec items if container method didn't work
        if not specifications:
            for items_selector in specs_items_selectors:
                try:
                    specs = self._extract_specs_from_items(parser, items_selector, detail_selectors)
                    if specs:
                        specifications.extend(specs)
                        break
                except Exception as e:
                    self.logger.debug(f"Failed to extract specs from items '{items_selector}': {e}")
                    continue
        
        return specifications
    
    def _extract_specs_from_container(self, container, selectors) -> List[Dict[str, Any]]:
        """Extract specifications from a container element."""
        specifications = []
        
        # Look for grouped specifications
        groups_selectors = selectors.get('specs_groups', [])
        for group_selector in groups_selectors:
            try:
                groups = container.css(group_selector)
                for group in groups:
                    group_name = self._extract_spec_group_name(group)
                    group_specs = self._extract_specs_from_group(group, selectors)
                    
                    for spec in group_specs:
                        spec['group'] = group_name
                        specifications.append(spec)
                        
                if specifications:
                    return specifications
            except Exception as e:
                self.logger.debug(f"Failed to extract grouped specs: {e}")
                continue
        
        # Fallback: extract all specs from container without grouping
        items_selectors = selectors.get('specs_items', [])
        for items_selector in items_selectors:
            try:
                items = container.css(items_selector)
                for item in items:
                    spec = self._extract_spec_from_item(item, selectors)
                    if spec:
                        specifications.append(spec)
            except Exception:
                continue
        
        return specifications
    
    def _extract_specs_from_items(self, parser, items_selector: str, selectors) -> List[Dict[str, Any]]:
        """Extract specifications from individual items."""
        specifications = []
        
        try:
            items = parser.css(items_selector)
            for item in items:
                spec = self._extract_spec_from_item(item, selectors)
                if spec:
                    specifications.append(spec)
        except Exception as e:
            self.logger.debug(f"Failed to extract specs from items: {e}")
        
        return specifications
    
    def _extract_spec_from_item(self, item, selectors) -> Optional[Dict[str, Any]]:
        """Extract a single specification from an item."""
        key_selectors = selectors.get('specs_key', [])
        value_selectors = selectors.get('specs_value', [])
        
        # Extract key
        spec_key = None
        for key_selector in key_selectors:
            try:
                key_elem = item.css_first(key_selector)
                if key_elem:
                    spec_key = normalize_spec_key(key_elem.text())
                    if spec_key:
                        break
            except Exception:
                continue
        
        # Extract value
        spec_value = None
        for value_selector in value_selectors:
            try:
                value_elem = item.css_first(value_selector)
                if value_elem:
                    spec_value = normalize_spec_value(value_elem.text())
                    if spec_value:
                        break
            except Exception:
                continue
        
        # If no specific selectors worked, try to extract from the item itself
        if not spec_key or not spec_value:
            item_text = normalize_text(item.text())
            if item_text and ':' in item_text:
                parts = item_text.split(':', 1)
                if len(parts) == 2:
                    spec_key = normalize_spec_key(parts[0])
                    spec_value = normalize_spec_value(parts[1])
        
        if spec_key and spec_value:
            return {
                "key": spec_key,
                "value": spec_value,
                "group": None
            }
        
        return None
    
    def _extract_spec_group_name(self, group_element) -> Optional[str]:
        """Extract specification group name."""
        # Look for group title/header
        group_title_selectors = ['h3', 'h4', '.group-title', '.spec-group-title', 'strong']
        
        for selector in group_title_selectors:
            try:
                title_elem = group_element.css_first(selector)
                if title_elem:
                    title = normalize_text(title_elem.text())
                    if title and len(title) > 2:
                        return title
            except Exception:
                continue
        
        return "General"
    
    def _extract_specs_from_group(self, group_element, selectors) -> List[Dict[str, Any]]:
        """Extract specifications from a group element."""
        specs = []
        
        items_selectors = selectors.get('specs_items', [])
        for items_selector in items_selectors:
            try:
                items = group_element.css(items_selector)
                for item in items:
                    spec = self._extract_spec_from_item(item, selectors)
                    if spec:
                        specs.append(spec)
                        
                if specs:
                    break
            except Exception:
                continue
        
        return specs
    
    def _extract_images(self, parser, base_url: str) -> List[Dict[str, Any]]:
        """Extract product images."""
        detail_selectors = self.selectors.get('product_detail', {})
        images = []
        
        # Main image
        main_image_selectors = detail_selectors.get('main_image', [])
        main_image_url = self._extract_with_selectors(parser, main_image_selectors, attribute='src')
        
        # Also check data-src for lazy loading
        if not main_image_url:
            main_image_url = self._extract_with_selectors(parser, main_image_selectors, attribute='data-src')
        
        if main_image_url:
            if not main_image_url.startswith(('http://', 'https://')):
                main_image_url = urljoin(base_url, main_image_url)
            
            images.append({
                "url": main_image_url,
                "position": 0,
                "type": "main"
            })
        
        # Gallery images
        gallery_selectors = detail_selectors.get('gallery_images', [])
        gallery_urls = self._extract_with_selectors(parser, gallery_selectors, attribute='src', multiple=True)
        
        # Also check data-src for lazy loading
        if not gallery_urls:
            gallery_urls = self._extract_with_selectors(parser, gallery_selectors, attribute='data-src', multiple=True)
        
        if gallery_urls:
            for i, image_url in enumerate(gallery_urls):
                if not image_url.startswith(('http://', 'https://')):
                    image_url = urljoin(base_url, image_url)
                
                # Skip if already added as main image
                if image_url not in [img['url'] for img in images]:
                    images.append({
                        "url": image_url,
                        "position": i + 1,
                        "type": "gallery"
                    })
        
        return images
    
    def _extract_descriptions(self, parser) -> Dict[str, Any]:
        """Extract product descriptions."""
        detail_selectors = self.selectors.get('product_detail', {})
        
        descriptions = {}
        
        # Short description
        short_desc_selectors = detail_selectors.get('short_description', [])
        short_desc = self._extract_with_selectors(parser, short_desc_selectors)
        if short_desc:
            descriptions['short_desc'] = normalize_text(short_desc)
        
        # Full description (may contain HTML)
        full_desc_selectors = detail_selectors.get('full_description', [])
        for selector in full_desc_selectors:
            try:
                desc_elem = parser.css_first(selector)
                if desc_elem:
                    # Get HTML content
                    descriptions['full_desc_html'] = desc_elem.html
                    # Also get text content
                    descriptions['full_desc_text'] = normalize_text(desc_elem.text())
                    break
            except Exception:
                continue
        
        return descriptions
    
    def _extract_availability_info(self, parser) -> Dict[str, Any]:
        """Extract availability and logistics information."""
        detail_selectors = self.selectors.get('product_detail', {})
        
        info = {}
        
        # Availability status
        availability_selectors = detail_selectors.get('availability', [])
        availability_text = self._extract_with_selectors(parser, availability_selectors)
        if availability_text:
            info['availability'] = normalize_availability(availability_text)
            info['availability_text'] = availability_text
        
        # Warranty information
        warranty_selectors = detail_selectors.get('warranty', [])
        warranty_text = self._extract_with_selectors(parser, warranty_selectors)
        if warranty_text:
            info['warranty_info'] = normalize_warranty(warranty_text)
        
        # Origin/Made in
        origin_selectors = detail_selectors.get('origin', [])
        origin_text = self._extract_with_selectors(parser, origin_selectors)
        if origin_text:
            info['origin'] = normalize_text(origin_text)
        
        return info
    
    def _extract_ratings(self, parser) -> Dict[str, Any]:
        """Extract ratings and review information."""
        detail_selectors = self.selectors.get('product_detail', {})
        
        ratings = {}
        
        # Rating average
        rating_selectors = detail_selectors.get('rating', [])
        rating_text = self._extract_with_selectors(parser, rating_selectors)
        if rating_text:
            ratings['rating_avg'] = normalize_rating(rating_text)
            ratings['rating_text'] = rating_text
        
        # Rating count
        rating_count_selectors = detail_selectors.get('rating_count', [])
        rating_count_text = self._extract_with_selectors(parser, rating_count_selectors)
        if rating_count_text:
            # Extract number from text
            count_match = re.search(r'(\d+)', rating_count_text)
            if count_match:
                ratings['rating_count'] = int(count_match.group(1))
                ratings['rating_count_text'] = rating_count_text
        
        return ratings
    
    def _extract_category_path(self, parser) -> Optional[str]:
        """Extract category path from breadcrumb."""
        detail_selectors = self.selectors.get('product_detail', {})
        
        category_path_selectors = detail_selectors.get('category_path', [])
        category_path = self._extract_with_selectors(parser, category_path_selectors)
        
        if category_path:
            return normalize_category_path(category_path)
        
        return None
    
    def _extract_structured_data(self, parser) -> Optional[Dict[str, Any]]:
        """Extract structured data (JSON-LD) if available."""
        try:
            # Look for JSON-LD script tags
            script_tags = parser.css('script[type="application/ld+json"]')
            
            for script in script_tags:
                script_content = script.text()
                if script_content:
                    try:
                        data = json.loads(script_content)
                        if isinstance(data, dict) and data.get('@type') == 'Product':
                            return data
                    except json.JSONDecodeError:
                        continue
        
        except Exception as e:
            self.logger.debug(f"Failed to extract structured data: {e}")
        
        return None