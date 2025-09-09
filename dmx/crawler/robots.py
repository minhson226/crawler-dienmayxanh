"""
Robots.txt checker for respecting crawling rules
"""
import httpx
import logging
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin
from typing import Optional

logger = logging.getLogger(__name__)


class RobotsChecker:
    """Check robots.txt compliance"""
    
    def __init__(self, base_url: str, user_agent: str = "*"):
        """
        Initialize robots checker
        
        Args:
            base_url: Base URL of the site
            user_agent: User agent string to check rules for
        """
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.robots_parser: Optional[RobotFileParser] = None
        self.crawl_delay: Optional[float] = None
        self._loaded = False
    
    async def load_robots_txt(self):
        """Load and parse robots.txt"""
        try:
            robots_url = urljoin(self.base_url, "/robots.txt")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(robots_url)
                
                if response.status_code == 200:
                    robots_content = response.text
                    
                    # Parse robots.txt
                    self.robots_parser = RobotFileParser()
                    self.robots_parser.set_url(robots_url)
                    
                    # Set content manually since we're using async
                    lines = robots_content.split('\n')
                    for line in lines:
                        self.robots_parser.read(line)
                    
                    # Get crawl delay
                    try:
                        self.crawl_delay = self.robots_parser.crawl_delay(self.user_agent)
                        if self.crawl_delay:
                            logger.info(f"Robots.txt crawl-delay: {self.crawl_delay}s")
                    except Exception:
                        self.crawl_delay = None
                    
                    self._loaded = True
                    logger.info(f"Loaded robots.txt from {robots_url}")
                    
                else:
                    logger.warning(f"Could not load robots.txt: HTTP {response.status_code}")
                    
        except Exception as e:
            logger.warning(f"Error loading robots.txt: {e}")
    
    def can_fetch(self, url: str) -> bool:
        """
        Check if URL can be fetched according to robots.txt
        
        Args:
            url: URL to check
            
        Returns:
            True if URL can be fetched, False otherwise
        """
        if not self._loaded:
            # If robots.txt couldn't be loaded, allow crawling
            return True
        
        if not self.robots_parser:
            return True
        
        try:
            return self.robots_parser.can_fetch(self.user_agent, url)
        except Exception as e:
            logger.warning(f"Error checking robots.txt for {url}: {e}")
            return True
    
    def get_crawl_delay(self) -> Optional[float]:
        """Get crawl delay from robots.txt"""
        return self.crawl_delay
    
    async def ensure_loaded(self):
        """Ensure robots.txt is loaded"""
        if not self._loaded:
            await self.load_robots_txt()