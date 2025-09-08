"""
URL normalization utilities
"""
import re
from urllib.parse import urlparse, urljoin, quote, unquote
from typing import Optional

class URLNormalizer:
    """Normalize and clean URLs"""
    
    def __init__(self, base_url: str):
        """Initialize with base URL"""
        self.base_url = base_url.rstrip("/")
    
    def normalize(self, url: str) -> str:
        """Normalize URL to canonical form"""
        try:
            # Make absolute URL
            if url.startswith("/"):
                url = urljoin(self.base_url, url)
            
            # Parse URL
            parsed = urlparse(url)
            
            # Remove fragment
            url = url.split("#")[0]
            
            # Remove common tracking parameters
            if parsed.query:
                query_params = []
                for param in parsed.query.split("&"):
                    if "=" in param:
                        key, value = param.split("=", 1)
                        # Skip tracking parameters
                        if not self._is_tracking_param(key):
                            query_params.append(param)
                
                if query_params:
                    url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{'&'.join(query_params)}"
                else:
                    url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            # Remove trailing slash for non-root paths
            if url.endswith("/") and len(parsed.path) > 1:
                url = url.rstrip("/")
            
            return url
            
        except Exception:
            return url
    
    def _is_tracking_param(self, param: str) -> bool:
        """Check if parameter is a tracking parameter"""
        tracking_params = {
            "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
            "fbclid", "gclid", "ref", "referrer", "source", "campaign",
            "mc_cid", "mc_eid", "_ga", "_gid", "affiliate_id"
        }
        return param.lower() in tracking_params
    
    def get_slug(self, url: str) -> str:
        """Extract slug from URL"""
        try:
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.split("/") if p]
            if path_parts:
                return path_parts[-1]
            return ""
        except Exception:
            return ""
    
    def is_same_domain(self, url: str) -> bool:
        """Check if URL is from the same domain"""
        try:
            base_domain = urlparse(self.base_url).netloc
            url_domain = urlparse(url).netloc
            return base_domain == url_domain
        except Exception:
            return False
    
    def clean_path(self, path: str) -> str:
        """Clean and normalize URL path"""
        try:
            # Decode URL encoding
            path = unquote(path)
            
            # Remove multiple slashes
            path = re.sub(r'/+', '/', path)
            
            # Remove trailing slash (except root)
            if len(path) > 1 and path.endswith("/"):
                path = path.rstrip("/")
            
            return path
            
        except Exception:
            return path