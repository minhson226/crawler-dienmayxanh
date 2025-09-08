"""
Product detail page parser
"""
import logging
import hashlib
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
from selectolax.parser import HTMLParser
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


class ProductDetailParser:
    """Parser for product detail pages"""
    
    def __init__(self):
        """Initialize product parser with selectors"""
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
                    "product_detail": {
                        "name": ["h1", ".product-name", ".detail-title h1"],
                        "price_regular": [".price", ".box-price-present", ".price-current"],
                        "price_promo": [".price-sale", ".price-promo"],
                        "price_old": [".price-old", ".box-price-old", ".price-before"],
                        "discount_percent": [".percent", ".box-price-percent", ".discount-percent"],
                        "brand": ["[data-brand]", ".brand", "a[href*='brand']"],
                        "specifications": [".parameter", ".specifications", ".specs"],
                        "specs_kv": [".parameter__list li", ".specs tr", ".spec-item"],
                        "gallery_images": [".gallery img", ".product-images img", ".item-img img"],
                        "rating": [".rating", ".rating-star", ".vote-txt"]
                    }
                }
        except Exception as e:
            logger.error(f"Error loading selectors: {e}")
            return {}
    
    def parse_product(self, html: str, product_url: str) -> Optional[Dict[str, Any]]:
        """Parse complete product data from product page"""
        try:
            parser = HTMLParser(html)
            
            # Extract basic product info
            product_data = {
                "url": product_url,
                "canonical_url": self._get_canonical_url(parser, product_url),
                "slug": self._extract_slug(product_url),
                "crawled_at": datetime.utcnow()
            }
            
            # Extract product name
            product_data["name"] = self._extract_name(parser)
            if not product_data["name"]:
                logger.warning(f"No product name found for {product_url}")
                return None
            
            # Extract pricing
            pricing = self._extract_pricing(parser)
            product_data.update(pricing)
            
            # Extract brand
            product_data["brand"] = self._extract_brand(parser)
            
            # Extract product code/SKU
            product_data["product_code"] = self._extract_product_code(parser, html)
            
            # Extract descriptions
            descriptions = self._extract_descriptions(parser)
            product_data.update(descriptions)
            
            # Extract specifications
            specifications = self._extract_specifications(parser)
            product_data["specifications"] = specifications
            
            # Extract images
            product_data["images"] = self._extract_images(parser, product_url)
            
            # Extract ratings
            rating_data = self._extract_ratings(parser)
            product_data.update(rating_data)
            
            # Extract availability and shipping
            product_data["availability"] = self._extract_availability(parser)
            product_data["warranty_info"] = self._extract_warranty(parser)
            product_data["shipping_info"] = self._extract_shipping(parser)
            
            # Extract SEO data
            seo_data = self._extract_seo_data(parser)
            product_data.update(seo_data)
            
            # Generate content hash for change detection
            product_data["hash_content"] = self._generate_content_hash(product_data)
            
            logger.info(f"Parsed product: {product_data['name'][:50]}...")
            return product_data
            
        except Exception as e:
            logger.error(f"Error parsing product {product_url}: {e}")
            return None
    
    def _extract_name(self, parser: HTMLParser) -> str:
        """Extract product name"""
        selectors = self.selectors.get("product_detail", {}).get("name", [])
        
        for selector in selectors:
            try:
                element = parser.css_first(selector)
                if element:
                    name = element.text(strip=True)
                    if name and len(name) > 3:
                        return name
            except Exception:
                continue
        
        return ""
    
    def _extract_pricing(self, parser: HTMLParser) -> Dict[str, float]:
        """Extract pricing information"""
        pricing = {}
        
        # Regular price
        regular_selectors = self.selectors.get("product_detail", {}).get("price_regular", [])
        for selector in regular_selectors:
            try:
                element = parser.css_first(selector)
                if element:
                    price = self._parse_price(element.text())
                    if price:
                        pricing["price_regular"] = price
                        break
            except Exception:
                continue
        
        # Promo price
        promo_selectors = self.selectors.get("product_detail", {}).get("price_promo", [])
        for selector in promo_selectors:
            try:
                element = parser.css_first(selector)
                if element:
                    price = self._parse_price(element.text())
                    if price:
                        pricing["price_promo"] = price
                        break
            except Exception:
                continue
        
        # Old price
        old_selectors = self.selectors.get("product_detail", {}).get("price_old", [])
        for selector in old_selectors:
            try:
                element = parser.css_first(selector)
                if element:
                    price = self._parse_price(element.text())
                    if price:
                        pricing["price_old"] = price
                        break
            except Exception:
                continue
        
        # Discount percentage
        discount_selectors = self.selectors.get("product_detail", {}).get("discount_percent", [])
        for selector in discount_selectors:
            try:
                element = parser.css_first(selector)
                if element:
                    text = element.text(strip=True)
                    percent = self._parse_percentage(text)
                    if percent:
                        pricing["discount_percent"] = percent
                        break
            except Exception:
                continue
        
        return pricing
    
    def _parse_price(self, price_text: str) -> Optional[float]:
        """Parse price from text"""
        if not price_text:
            return None
        
        try:
            # Remove currency symbols and formatting
            cleaned = re.sub(r'[^\d,.]', '', price_text)
            cleaned = cleaned.replace(',', '').replace('.', '')
            
            if cleaned.isdigit():
                return float(cleaned)
            
            # Try to find price pattern
            price_match = re.search(r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)', price_text)
            if price_match:
                price_str = price_match.group(1).replace(',', '').replace('.', '')
                return float(price_str)
        
        except Exception:
            pass
        
        return None
    
    def _parse_percentage(self, text: str) -> Optional[float]:
        """Parse percentage from text"""
        if not text:
            return None
        
        try:
            # Find percentage pattern
            percent_match = re.search(r'(\d+(?:\.\d+)?)%?', text)
            if percent_match:
                return float(percent_match.group(1))
        except Exception:
            pass
        
        return None
    
    def _extract_brand(self, parser: HTMLParser) -> str:
        """Extract brand information"""
        selectors = self.selectors.get("product_detail", {}).get("brand", [])
        
        for selector in selectors:
            try:
                element = parser.css_first(selector)
                if element:
                    # Try data attribute first
                    brand = element.attributes.get("data-brand")
                    if brand:
                        return brand.strip()
                    
                    # Try text content
                    text = element.text(strip=True)
                    if text and len(text) > 1:
                        return text
            except Exception:
                continue
        
        return ""
    
    def _extract_product_code(self, parser: HTMLParser, html: str) -> str:
        """Extract product code/SKU"""
        # Try JSON-LD data first
        try:
            import json
            json_scripts = parser.css('script[type="application/ld+json"]')
            for script in json_scripts:
                try:
                    data = json.loads(script.text())
                    if isinstance(data, dict):
                        sku = data.get("sku") or data.get("productID") or data.get("mpn")
                        if sku:
                            return str(sku)
                except Exception:
                    continue
        except Exception:
            pass
        
        # Try to find in JavaScript variables
        try:
            js_match = re.search(r'(?:productId|product_id|sku|itemId)["\']?\s*[:=]\s*["\']?(\w+)', html, re.IGNORECASE)
            if js_match:
                return js_match.group(1)
        except Exception:
            pass
        
        # Try meta tags
        try:
            meta_selectors = [
                'meta[name="product:id"]',
                'meta[property="product:id"]',
                'meta[name="sku"]'
            ]
            for selector in meta_selectors:
                element = parser.css_first(selector)
                if element:
                    content = element.attributes.get("content")
                    if content:
                        return content.strip()
        except Exception:
            pass
        
        return ""
    
    def _extract_descriptions(self, parser: HTMLParser) -> Dict[str, str]:
        """Extract product descriptions"""
        descriptions = {}
        
        # Short description
        short_selectors = [".short-desc", ".product-summary", ".product-intro"]
        for selector in short_selectors:
            try:
                element = parser.css_first(selector)
                if element:
                    text = element.text(strip=True)
                    if text and len(text) > 10:
                        descriptions["short_desc"] = text
                        break
            except Exception:
                continue
        
        # Full description
        full_selectors = [".product-desc", ".description", ".product-content", ".detail-content"]
        for selector in full_selectors:
            try:
                element = parser.css_first(selector)
                if element:
                    html_content = element.html
                    if html_content and len(html_content) > 20:
                        descriptions["full_desc_html"] = html_content
                        break
            except Exception:
                continue
        
        return descriptions
    
    def _extract_specifications(self, parser: HTMLParser) -> List[Dict[str, str]]:
        """Extract product specifications"""
        specifications = []
        
        # Try specification selectors
        spec_selectors = self.selectors.get("product_detail", {}).get("specifications", [])
        
        for selector in spec_selectors:
            try:
                spec_container = parser.css_first(selector)
                if spec_container:
                    # Try key-value selectors
                    kv_selectors = self.selectors.get("product_detail", {}).get("specs_kv", [])
                    
                    for kv_selector in kv_selectors:
                        try:
                            spec_items = spec_container.css(kv_selector)
                            for item in spec_items:
                                spec_data = self._parse_spec_item(item)
                                if spec_data:
                                    specifications.append(spec_data)
                            
                            if specifications:
                                break
                                
                        except Exception:
                            continue
                    
                    if specifications:
                        break
                        
            except Exception:
                continue
        
        return specifications
    
    def _parse_spec_item(self, item) -> Optional[Dict[str, str]]:
        """Parse individual specification item"""
        try:
            # Try table row format
            cells = item.css("td, th")
            if len(cells) >= 2:
                key = cells[0].text(strip=True)
                value = cells[1].text(strip=True)
                if key and value:
                    return {
                        "spec_key": key,
                        "spec_value": value,
                        "spec_group": ""
                    }
            
            # Try list format with colon separator
            text = item.text(strip=True)
            if ":" in text:
                parts = text.split(":", 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if key and value:
                        return {
                            "spec_key": key,
                            "spec_value": value,
                            "spec_group": ""
                        }
            
            return None
            
        except Exception:
            return None
    
    def _extract_images(self, parser: HTMLParser, base_url: str) -> List[Dict[str, str]]:
        """Extract product images"""
        images = []
        
        selectors = self.selectors.get("product_detail", {}).get("gallery_images", [])
        
        for selector in selectors:
            try:
                img_elements = parser.css(selector)
                for i, img in enumerate(img_elements):
                    src = img.attributes.get("src") or img.attributes.get("data-src")
                    if src:
                        if src.startswith("/"):
                            src = urljoin(base_url, src)
                        
                        alt = img.attributes.get("alt", "")
                        
                        images.append({
                            "image_url": src,
                            "alt": alt,
                            "position": i,
                            "is_primary": i == 0
                        })
                
                if images:
                    break
                    
            except Exception:
                continue
        
        return images
    
    def _extract_ratings(self, parser: HTMLParser) -> Dict[str, Any]:
        """Extract rating information"""
        rating_data = {}
        
        selectors = self.selectors.get("product_detail", {}).get("rating", [])
        
        for selector in selectors:
            try:
                rating_element = parser.css_first(selector)
                if rating_element:
                    # Try to find rating value
                    rating_text = rating_element.text(strip=True)
                    
                    # Look for rating pattern
                    rating_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:/\s*5|★)', rating_text)
                    if rating_match:
                        rating_data["rating_avg"] = float(rating_match.group(1))
                    
                    # Look for review count
                    count_match = re.search(r'(\d+)\s*(?:đánh giá|review|bình luận)', rating_text)
                    if count_match:
                        rating_data["review_count"] = int(count_match.group(1))
                    
                    break
                    
            except Exception:
                continue
        
        return rating_data
    
    def _extract_availability(self, parser: HTMLParser) -> str:
        """Extract availability status"""
        availability_selectors = [".availability", ".stock-status", ".product-status"]
        
        for selector in availability_selectors:
            try:
                element = parser.css_first(selector)
                if element:
                    text = element.text(strip=True)
                    if text:
                        return text
            except Exception:
                continue
        
        return ""
    
    def _extract_warranty(self, parser: HTMLParser) -> str:
        """Extract warranty information"""
        warranty_selectors = [".warranty", ".guarantee", "[class*='warranty']"]
        
        for selector in warranty_selectors:
            try:
                element = parser.css_first(selector)
                if element:
                    text = element.text(strip=True)
                    if text and len(text) > 5:
                        return text
            except Exception:
                continue
        
        return ""
    
    def _extract_shipping(self, parser: HTMLParser) -> str:
        """Extract shipping information"""
        shipping_selectors = [".shipping", ".delivery", "[class*='shipping']"]
        
        for selector in shipping_selectors:
            try:
                element = parser.css_first(selector)
                if element:
                    text = element.text(strip=True)
                    if text and len(text) > 5:
                        return text
            except Exception:
                continue
        
        return ""
    
    def _extract_seo_data(self, parser: HTMLParser) -> Dict[str, str]:
        """Extract SEO metadata"""
        seo_data = {}
        
        # Title
        title_element = parser.css_first("title")
        if title_element:
            seo_data["meta_title"] = title_element.text(strip=True)
        
        # Meta description
        meta_desc = parser.css_first('meta[name="description"]')
        if meta_desc:
            seo_data["meta_desc"] = meta_desc.attributes.get("content", "")
        
        return seo_data
    
    def _get_canonical_url(self, parser: HTMLParser, default_url: str) -> str:
        """Get canonical URL"""
        canonical = parser.css_first('link[rel="canonical"]')
        if canonical:
            href = canonical.attributes.get("href")
            if href:
                return href
        
        return default_url
    
    def _extract_slug(self, url: str) -> str:
        """Extract slug from URL"""
        try:
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.split("/") if p]
            if path_parts:
                return path_parts[-1]
        except Exception:
            pass
        
        return ""
    
    def _generate_content_hash(self, product_data: Dict[str, Any]) -> str:
        """Generate MD5 hash of key product content for change detection"""
        try:
            # Use key fields for hash
            content_string = f"{product_data.get('name', '')}" \
                           f"{product_data.get('price_regular', '')}" \
                           f"{product_data.get('price_promo', '')}" \
                           f"{product_data.get('short_desc', '')}"
            
            return hashlib.md5(content_string.encode('utf-8')).hexdigest()
        except Exception:
            return ""