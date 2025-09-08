"""Robots.txt parser and checker."""

import asyncio
import time
from typing import Optional, Dict, Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from dmx.utils.config import get_config


class RobotsChecker:
    """Robots.txt compliance checker."""
    
    def __init__(self, user_agent: str = "*"):
        self.user_agent = user_agent
        self.robots_cache: Dict[str, Dict[str, Any]] = {}
        self.config = get_config()
    
    async def can_fetch(self, url: str, user_agent: Optional[str] = None) -> bool:
        """Check if URL can be fetched according to robots.txt."""
        if not self.config.robots.respect:
            return True
        
        user_agent = user_agent or self.user_agent
        
        try:
            domain = self._get_domain(url)
            robots_data = await self._get_robots_data(domain)
            
            if not robots_data:
                # If no robots.txt, assume allowed
                return True
            
            rp = robots_data.get('parser')
            if rp:
                return rp.can_fetch(user_agent, url)
            
            return True
            
        except Exception as e:
            # If robots.txt check fails, err on the side of caution and allow
            return True
    
    async def get_crawl_delay(self, url: str, user_agent: Optional[str] = None) -> Optional[float]:
        """Get crawl delay for URL according to robots.txt."""
        if not self.config.robots.respect:
            return None
        
        user_agent = user_agent or self.user_agent
        
        try:
            domain = self._get_domain(url)
            robots_data = await self._get_robots_data(domain)
            
            if not robots_data:
                return None
            
            rp = robots_data.get('parser')
            if rp:
                delay = rp.crawl_delay(user_agent)
                if delay:
                    return float(delay)
            
            # Check for custom crawl delay override
            if self.config.robots.crawl_delay_override:
                return float(self.config.robots.crawl_delay_override)
            
            return None
            
        except Exception:
            return None
    
    async def get_request_rate(self, url: str, user_agent: Optional[str] = None) -> Optional[float]:
        """Get request rate for URL according to robots.txt."""
        if not self.config.robots.respect:
            return None
        
        user_agent = user_agent or self.user_agent
        
        try:
            domain = self._get_domain(url)
            robots_data = await self._get_robots_data(domain)
            
            if not robots_data:
                return None
            
            rp = robots_data.get('parser')
            if rp:
                rate = rp.request_rate(user_agent)
                if rate:
                    return float(rate.requests) / float(rate.seconds)
            
            return None
            
        except Exception:
            return None
    
    async def _get_robots_data(self, domain: str) -> Optional[Dict[str, Any]]:
        """Get robots.txt data for domain with caching."""
        now = time.time()
        
        # Check cache
        if domain in self.robots_cache:
            cached_data = self.robots_cache[domain]
            cache_time = cached_data.get('cached_at', 0)
            
            # Cache is still valid
            if now - cache_time < self.config.robots.check_interval:
                return cached_data
        
        # Fetch robots.txt
        robots_url = f"https://{domain}/robots.txt"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(robots_url)
                
                if response.status_code == 200:
                    robots_content = response.text
                    
                    # Parse robots.txt
                    rp = RobotFileParser()
                    rp.set_url(robots_url)
                    
                    # RobotFileParser.read() expects a list of lines
                    rp.set_url(robots_url)
                    robots_lines = robots_content.splitlines()
                    
                    # Create a mock file-like object for the parser
                    class MockFile:
                        def __init__(self, lines):
                            self.lines = lines
                            self.index = 0
                        
                        def readline(self):
                            if self.index < len(self.lines):
                                line = self.lines[self.index] + '\n'
                                self.index += 1
                                return line
                            return ''
                    
                    mock_file = MockFile(robots_lines)
                    rp.read = lambda: None  # Override read method
                    
                    # Manually parse the content
                    for line in robots_lines:
                        rp._add_entry(line)
                    
                    # Simple manual parsing as fallback
                    parsed_data = self._simple_robots_parse(robots_content)
                    
                    robots_data = {
                        'content': robots_content,
                        'parser': None,  # RobotFileParser can be finicky, use manual parsing
                        'parsed': parsed_data,
                        'cached_at': now
                    }
                    
                    self.robots_cache[domain] = robots_data
                    return robots_data
                
                else:
                    # No robots.txt or error, cache negative result
                    robots_data = {
                        'content': None,
                        'parser': None,
                        'parsed': {},
                        'cached_at': now
                    }
                    
                    self.robots_cache[domain] = robots_data
                    return None
                    
        except Exception as e:
            # Error fetching robots.txt, cache negative result
            robots_data = {
                'content': None,
                'parser': None,
                'parsed': {},
                'cached_at': now,
                'error': str(e)
            }
            
            self.robots_cache[domain] = robots_data
            return None
    
    def _simple_robots_parse(self, robots_content: str) -> Dict[str, Any]:
        """Simple robots.txt parser as fallback."""
        rules = {
            'disallow': [],
            'allow': [],
            'crawl_delay': None,
            'user_agents': set()
        }
        
        current_user_agent = None
        
        for line in robots_content.splitlines():
            line = line.strip()
            
            if not line or line.startswith('#'):
                continue
            
            if ':' not in line:
                continue
            
            key, value = line.split(':', 1)
            key = key.strip().lower()
            value = value.strip()
            
            if key == 'user-agent':
                current_user_agent = value
                rules['user_agents'].add(value)
            
            elif key == 'disallow' and current_user_agent:
                if current_user_agent == '*' or current_user_agent == self.user_agent:
                    rules['disallow'].append(value)
            
            elif key == 'allow' and current_user_agent:
                if current_user_agent == '*' or current_user_agent == self.user_agent:
                    rules['allow'].append(value)
            
            elif key == 'crawl-delay' and current_user_agent:
                if current_user_agent == '*' or current_user_agent == self.user_agent:
                    try:
                        rules['crawl_delay'] = float(value)
                    except ValueError:
                        pass
        
        return rules
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc
    
    def can_fetch_simple(self, url: str, robots_data: Optional[Dict[str, Any]] = None) -> bool:
        """Simple synchronous robots.txt check using cached data."""
        if not self.config.robots.respect:
            return True
        
        if not robots_data:
            return True
        
        parsed_rules = robots_data.get('parsed', {})
        if not parsed_rules:
            return True
        
        path = urlparse(url).path
        
        # Check disallow rules
        for disallow_pattern in parsed_rules.get('disallow', []):
            if disallow_pattern and path.startswith(disallow_pattern):
                # Check if there's a more specific allow rule
                for allow_pattern in parsed_rules.get('allow', []):
                    if allow_pattern and path.startswith(allow_pattern):
                        return True
                return False
        
        return True
    
    def get_crawl_delay_simple(self, robots_data: Optional[Dict[str, Any]] = None) -> Optional[float]:
        """Simple synchronous crawl delay check using cached data."""
        if not self.config.robots.respect:
            return None
        
        if not robots_data:
            return None
        
        parsed_rules = robots_data.get('parsed', {})
        crawl_delay = parsed_rules.get('crawl_delay')
        
        if crawl_delay:
            return crawl_delay
        
        # Check for override
        if self.config.robots.crawl_delay_override:
            return float(self.config.robots.crawl_delay_override)
        
        return None