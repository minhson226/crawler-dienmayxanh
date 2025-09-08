"""URL utilities for normalization and canonicalization."""

import re
import urllib.parse
from typing import Optional, Set
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs, urlencode


def normalize_url(url: str, base_url: Optional[str] = None) -> str:
    """Normalize URL by removing fragments, sorting query params, etc."""
    if not url:
        return url
    
    # Handle relative URLs
    if base_url and not url.startswith(('http://', 'https://')):
        url = urljoin(base_url, url)
    
    # Parse URL
    parsed = urlparse(url)
    
    # Remove fragment
    parsed = parsed._replace(fragment='')
    
    # Normalize path
    path = parsed.path
    if path:
        # Remove double slashes
        path = re.sub(r'/+', '/', path)
        # Remove trailing slash except for root
        if len(path) > 1 and path.endswith('/'):
            path = path.rstrip('/')
    
    # Sort query parameters for consistency
    if parsed.query:
        query_params = parse_qs(parsed.query, keep_blank_values=True)
        # Sort by key and flatten values
        sorted_params = []
        for key in sorted(query_params.keys()):
            for value in query_params[key]:
                sorted_params.append((key, value))
        query = urlencode(sorted_params)
    else:
        query = ''
    
    # Reconstruct URL
    normalized = urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        path,
        parsed.params,
        query,
        ''  # No fragment
    ))
    
    return normalized


def get_canonical_url(url: str, canonical_link: Optional[str] = None) -> str:
    """Get canonical URL, preferring provided canonical link."""
    if canonical_link:
        # Make sure canonical link is absolute
        if not canonical_link.startswith(('http://', 'https://')):
            canonical_link = urljoin(url, canonical_link)
        return normalize_url(canonical_link)
    
    return normalize_url(url)


def clean_query_params(url: str, remove_params: Optional[Set[str]] = None) -> str:
    """Remove specified query parameters from URL."""
    if remove_params is None:
        # Default params to remove
        remove_params = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'utm_flashsale', 'gclid', 'fbclid', '_ga', 'ref', 'source'
        }
    
    parsed = urlparse(url)
    
    if not parsed.query:
        return url
    
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    
    # Remove unwanted parameters
    cleaned_params = {
        key: values for key, values in query_params.items()
        if key not in remove_params
    }
    
    # Reconstruct query string
    if cleaned_params:
        query_items = []
        for key, values in cleaned_params.items():
            for value in values:
                query_items.append((key, value))
        query = urlencode(query_items)
    else:
        query = ''
    
    # Reconstruct URL
    cleaned = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        query,
        parsed.fragment
    ))
    
    return cleaned


def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs are from the same domain."""
    try:
        domain1 = urlparse(url1).netloc.lower()
        domain2 = urlparse(url2).netloc.lower()
        return domain1 == domain2
    except Exception:
        return False


def extract_domain(url: str) -> Optional[str]:
    """Extract domain from URL."""
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return None


def is_valid_url(url: str) -> bool:
    """Check if URL is valid."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def get_url_depth(url: str, base_url: str) -> int:
    """Get URL depth relative to base URL."""
    try:
        base_path = urlparse(base_url).path.rstrip('/')
        url_path = urlparse(url).path.rstrip('/')
        
        if url_path.startswith(base_path):
            relative_path = url_path[len(base_path):].lstrip('/')
            if not relative_path:
                return 0
            return len(relative_path.split('/'))
        
        return -1  # URL not under base
    except Exception:
        return -1


def build_product_url(base_url: str, category: str, product_slug: str) -> str:
    """Build product URL from components."""
    category = category.strip('/')
    product_slug = product_slug.strip('/')
    
    return urljoin(base_url, f"/{category}/{product_slug}")


def extract_product_slug(url: str) -> Optional[str]:
    """Extract product slug from URL."""
    try:
        path = urlparse(url).path.strip('/')
        parts = path.split('/')
        
        if len(parts) >= 2:
            return parts[-1]  # Last part is usually the product slug
        
        return None
    except Exception:
        return None


def extract_category_from_url(url: str) -> Optional[str]:
    """Extract category from URL."""
    try:
        path = urlparse(url).path.strip('/')
        parts = path.split('/')
        
        if len(parts) >= 1:
            return parts[0]  # First part is usually the category
        
        return None
    except Exception:
        return None


def is_product_url(url: str, product_patterns: Optional[list] = None) -> bool:
    """Check if URL looks like a product URL."""
    if product_patterns is None:
        # Default patterns for dienmayxanh.com
        product_patterns = [
            r'/[^/]+/[^/]+-[a-z0-9]+$',  # /category/product-name-code
            r'/[^/]+/[^/]+\?',           # /category/product with query params
        ]
    
    for pattern in product_patterns:
        if re.search(pattern, url):
            return True
    
    return False


def is_category_url(url: str, category_patterns: Optional[list] = None) -> bool:
    """Check if URL looks like a category URL."""
    if category_patterns is None:
        # Default patterns for dienmayxanh.com
        category_patterns = [
            r'/[^/]+/?$',                    # /category
            r'/[^/]+\?[^/]*$',              # /category with query params
            r'/[^/]+/[^/]+/?$',             # /category/subcategory
        ]
    
    for pattern in category_patterns:
        if re.search(pattern, url):
            return True
    
    return False


def should_crawl_url(url: str, include_patterns: list, exclude_patterns: list) -> bool:
    """Check if URL should be crawled based on include/exclude patterns."""
    # Check exclude patterns first
    for pattern in exclude_patterns:
        if pattern.startswith('*'):
            # Wildcard pattern
            if pattern[1:] in url:
                return False
        elif re.search(pattern, url):
            return False
    
    # Check include patterns
    if not include_patterns:
        return True  # No include patterns means include all
    
    for pattern in include_patterns:
        if pattern.startswith('*'):
            # Wildcard pattern
            if pattern[1:] in url:
                return True
        elif re.search(pattern, url):
            return True
    
    return False


def deduplicate_urls(urls: list) -> list:
    """Remove duplicate URLs while preserving order."""
    seen = set()
    result = []
    
    for url in urls:
        normalized = normalize_url(url)
        if normalized not in seen:
            seen.add(normalized)
            result.append(url)
    
    return result