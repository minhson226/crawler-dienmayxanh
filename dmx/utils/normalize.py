"""Text and data normalization utilities."""

import re
import html
from typing import Optional, Dict, Any, Union
from decimal import Decimal, InvalidOperation


def normalize_text(text: Optional[str]) -> Optional[str]:
    """Normalize text by cleaning whitespace and HTML entities."""
    if not text:
        return None
    
    # Decode HTML entities
    text = html.unescape(text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text if text else None


def normalize_price(price_text: Optional[str]) -> Optional[float]:
    """Extract and normalize price from text."""
    if not price_text:
        return None
    
    # Remove HTML tags
    price_text = re.sub(r'<[^>]+>', '', price_text)
    
    # Remove currency symbols and common price-related text
    price_text = re.sub(r'[₫VNDvndđ]', '', price_text)
    price_text = re.sub(r'[Tt]ừ|[Cc]hỉ|[Gg]iá|[Kk]huyến [Mm]ãi', '', price_text)
    
    # Extract numbers with dots or commas as thousand separators
    price_match = re.search(r'[\d.,]+', price_text)
    if not price_match:
        return None
    
    price_str = price_match.group()
    
    # Remove thousand separators (dots and commas)
    # Assume last separator is decimal if there are only 1-2 digits after it
    parts = re.split(r'[,.]', price_str)
    
    if len(parts) == 1:
        # No separators, just digits
        try:
            return float(parts[0])
        except ValueError:
            return None
    
    # If last part has 1-2 digits, it's likely decimal
    if len(parts[-1]) <= 2 and len(parts) > 1:
        # Treat as decimal
        integer_part = ''.join(parts[:-1])
        decimal_part = parts[-1]
        try:
            return float(f"{integer_part}.{decimal_part}")
        except ValueError:
            return None
    else:
        # All separators are thousands separators
        try:
            return float(''.join(parts))
        except ValueError:
            return None


def normalize_discount_percent(text: Optional[str]) -> Optional[float]:
    """Extract discount percentage from text."""
    if not text:
        return None
    
    # Look for percentage patterns
    percent_match = re.search(r'(\d+(?:\.\d+)?)\s*%', text)
    if percent_match:
        try:
            return float(percent_match.group(1))
        except ValueError:
            return None
    
    return None


def normalize_rating(rating_text: Optional[str]) -> Optional[float]:
    """Extract and normalize rating from text."""
    if not rating_text:
        return None
    
    # Look for rating patterns like "4.5/5", "4.5 sao", "4.5★"
    rating_match = re.search(r'(\d+(?:\.\d+)?)', rating_text)
    if rating_match:
        try:
            rating = float(rating_match.group(1))
            # Normalize to 5-point scale if needed
            if rating > 5:
                rating = rating / 2  # Assume 10-point scale
            return min(rating, 5.0)
        except ValueError:
            return None
    
    return None


def normalize_warranty(warranty_text: Optional[str]) -> Optional[str]:
    """Normalize warranty information."""
    if not warranty_text:
        return None
    
    warranty_text = normalize_text(warranty_text)
    
    # Common warranty patterns
    warranty_patterns = [
        r'(\d+)\s*năm',
        r'(\d+)\s*tháng',
        r'(\d+)\s*year',
        r'(\d+)\s*month',
    ]
    
    for pattern in warranty_patterns:
        match = re.search(pattern, warranty_text, re.IGNORECASE)
        if match:
            return warranty_text
    
    return warranty_text


def normalize_availability(availability_text: Optional[str]) -> str:
    """Normalize availability status."""
    if not availability_text:
        return "unknown"
    
    availability_text = normalize_text(availability_text).lower()
    
    # Map Vietnamese terms to standard statuses
    if any(term in availability_text for term in ['còn hàng', 'có sẵn', 'available', 'in stock']):
        return "in_stock"
    elif any(term in availability_text for term in ['hết hàng', 'out of stock', 'unavailable']):
        return "out_of_stock"
    elif any(term in availability_text for term in ['đặt trước', 'pre-order']):
        return "pre_order"
    elif any(term in availability_text for term in ['liên hệ', 'contact']):
        return "contact"
    else:
        return "unknown"


def normalize_brand(brand_text: Optional[str]) -> Optional[str]:
    """Normalize brand name."""
    if not brand_text:
        return None
    
    brand_text = normalize_text(brand_text)
    
    # Remove common prefixes/suffixes
    brand_text = re.sub(r'^(Hãng|Brand|Thương hiệu):\s*', '', brand_text, flags=re.IGNORECASE)
    brand_text = re.sub(r'\s*(Official|Chính hãng)$', '', brand_text, flags=re.IGNORECASE)
    
    return brand_text.title() if brand_text else None


def normalize_model(model_text: Optional[str]) -> Optional[str]:
    """Normalize model name."""
    if not model_text:
        return None
    
    model_text = normalize_text(model_text)
    
    # Remove common prefixes
    model_text = re.sub(r'^(Model|Mã|Code):\s*', '', model_text, flags=re.IGNORECASE)
    
    return model_text if model_text else None


def normalize_category_path(breadcrumb_text: Optional[str]) -> Optional[str]:
    """Normalize breadcrumb/category path."""
    if not breadcrumb_text:
        return None
    
    # Clean up breadcrumb text
    breadcrumb_text = normalize_text(breadcrumb_text)
    
    # Split by common separators and clean each part
    separators = [' > ', ' >> ', ' › ', ' / ', ' | ', ' - ']
    
    for separator in separators:
        if separator in breadcrumb_text:
            parts = breadcrumb_text.split(separator)
            # Clean each part and filter out empty ones
            cleaned_parts = [normalize_text(part) for part in parts if normalize_text(part)]
            return ' > '.join(cleaned_parts)
    
    return breadcrumb_text


def normalize_spec_key(spec_key: Optional[str]) -> Optional[str]:
    """Normalize specification key."""
    if not spec_key:
        return None
    
    spec_key = normalize_text(spec_key)
    
    # Remove trailing colons
    spec_key = spec_key.rstrip(':')
    
    return spec_key if spec_key else None


def normalize_spec_value(spec_value: Optional[str]) -> Optional[str]:
    """Normalize specification value."""
    if not spec_value:
        return None
    
    spec_value = normalize_text(spec_value)
    
    # Clean up common specification patterns
    spec_value = re.sub(r'^-\s*', '', spec_value)  # Remove leading dash
    spec_value = re.sub(r'\s*-\s*$', '', spec_value)  # Remove trailing dash
    
    return spec_value if spec_value else None


def extract_dimensions(text: Optional[str]) -> Dict[str, Optional[float]]:
    """Extract dimensions from text."""
    dimensions = {"width": None, "height": None, "depth": None, "weight": None}
    
    if not text:
        return dimensions
    
    text = normalize_text(text).lower()
    
    # Common dimension patterns
    patterns = {
        "width": [r'rộng\s*(\d+(?:\.\d+)?)', r'width\s*(\d+(?:\.\d+)?)', r'w\s*(\d+(?:\.\d+)?)'],
        "height": [r'cao\s*(\d+(?:\.\d+)?)', r'height\s*(\d+(?:\.\d+)?)', r'h\s*(\d+(?:\.\d+)?)'],
        "depth": [r'sâu\s*(\d+(?:\.\d+)?)', r'depth\s*(\d+(?:\.\d+)?)', r'd\s*(\d+(?:\.\d+)?)'],
        "weight": [r'nặng\s*(\d+(?:\.\d+)?)', r'weight\s*(\d+(?:\.\d+)?)', r'(\d+(?:\.\d+)?)\s*kg'],
    }
    
    for dimension, dim_patterns in patterns.items():
        for pattern in dim_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    dimensions[dimension] = float(match.group(1))
                    break
                except (ValueError, IndexError):
                    continue
    
    return dimensions


def clean_html_content(html_content: Optional[str]) -> Optional[str]:
    """Clean HTML content while preserving basic structure."""
    if not html_content:
        return None
    
    # Remove script and style tags completely
    html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove HTML comments
    html_content = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL)
    
    # Normalize whitespace
    html_content = re.sub(r'\s+', ' ', html_content)
    html_content = html_content.strip()
    
    return html_content if html_content else None


def normalize_product_name(name: Optional[str]) -> Optional[str]:
    """Normalize product name."""
    if not name:
        return None
    
    name = normalize_text(name)
    
    # Remove common redundant words/phrases
    redundant_phrases = [
        r'\s*-\s*Hàng\s+Chính\s+Hãng',
        r'\s*-\s*Chính\s+Hãng',
        r'\s*\([^)]*Chính\s+Hãng[^)]*\)',
        r'\s*\([^)]*Hàng\s+Chính\s+Hãng[^)]*\)',
    ]
    
    for phrase in redundant_phrases:
        name = re.sub(phrase, '', name, flags=re.IGNORECASE)
    
    # Clean up extra spaces
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name if name else None


def normalize_currency_amount(amount: Union[str, int, float]) -> Optional[float]:
    """Normalize currency amount to float."""
    if amount is None:
        return None
    
    if isinstance(amount, (int, float)):
        return float(amount)
    
    if isinstance(amount, str):
        return normalize_price(amount)
    
    return None