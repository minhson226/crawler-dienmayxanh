"""
Crawler runner - main orchestration module
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from dmx.db import get_session_context, Product, Category
from dmx.parsers.home import HomeParser
from dmx.parsers.category import CategoryParser
from dmx.parsers.listing import ListingParser
from dmx.parsers.product_detail import ProductDetailParser
from dmx.crawler.robots import RobotsChecker
from dmx.crawler.throttler import RequestThrottler
from dmx.utils.url import URLNormalizer

logger = logging.getLogger(__name__)


class CrawlerRunner:
    """Main crawler orchestration class"""
    
    def __init__(
        self,
        base_url: str = "https://www.dienmayxanh.com",
        max_products: int = 1000,
        max_pages_per_category: int = 50,
        concurrency: int = 3,
        respect_robots: bool = True,
        user_agent: str = None
    ):
        self.base_url = base_url
        self.max_products = max_products
        self.max_pages_per_category = max_pages_per_category
        self.concurrency = concurrency
        self.respect_robots = respect_robots
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        
        # Initialize components
        self.url_normalizer = URLNormalizer(base_url)
        self.throttler = RequestThrottler(
            concurrency=concurrency,
            delay_range=(1.0, 3.0)
        )
        
        if respect_robots:
            self.robots_checker = RobotsChecker(base_url, user_agent)
        else:
            self.robots_checker = None
            
        # Initialize parsers
        self.home_parser = HomeParser()
        self.category_parser = CategoryParser()
        self.listing_parser = ListingParser()
        self.product_parser = ProductDetailParser()
        
        # HTTP client
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": self.user_agent},
            follow_redirects=True
        )
        
        # Tracking
        self.session_id = str(int(time.time()))
        self.crawled_urls = set()
        self.stats = {
            "categories_found": 0,
            "products_crawled": 0,
            "errors": []
        }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def fetch_url(self, url: str) -> Optional[str]:
        """Fetch URL with retry logic"""
        try:
            # Check robots.txt
            if self.robots_checker and not self.robots_checker.can_fetch(url):
                logger.warning(f"Robots.txt disallows: {url}")
                return None
            
            # Throttle request
            await self.throttler.wait()
            
            # Make request
            response = await self.client.get(url)
            response.raise_for_status()
            
            logger.info(f"Fetched: {url} (status: {response.status_code})")
            return response.text
            
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            self.stats["errors"].append({"url": url, "error": str(e)})
            raise
    
    async def crawl_categories_only(self, max_level: int = 2) -> Dict[str, Any]:
        """Crawl categories only"""
        logger.info("Starting category crawl...")
        
        try:
            # Start from home page
            home_html = await self.fetch_url(self.base_url)
            if not home_html:
                raise Exception("Could not fetch home page")
            
            # Parse category links
            category_links = self.home_parser.extract_category_links(home_html, self.base_url)
            logger.info(f"Found {len(category_links)} category links on home page")
            
            categories_saved = 0
            
            with get_session_context() as session:
                # Save main categories
                for link_data in category_links:
                    try:
                        url = link_data["url"]
                        name = link_data["name"]
                        
                        # Check if category exists
                        existing = session.query(Category).filter(Category.url == url).first()
                        if existing:
                            continue
                        
                        # Create category
                        category = Category(
                            name=name,
                            url=url,
                            canonical_url=self.url_normalizer.normalize(url),
                            slug=self.url_normalizer.get_slug(url),
                            level=1,
                            breadcrumb_path=name
                        )
                        
                        session.add(category)
                        categories_saved += 1
                        
                    except Exception as e:
                        logger.error(f"Error saving category {link_data}: {e}")
                        self.stats["errors"].append({
                            "url": link_data.get("url", ""),
                            "error": str(e)
                        })
            
            self.stats["categories_found"] = categories_saved
            logger.info(f"Crawl completed. Found {categories_saved} categories")
            
            return self.stats
            
        except Exception as e:
            logger.error(f"Category crawl failed: {e}")
            raise
    
    async def crawl_category_products(self, category_url: str) -> Dict[str, Any]:
        """Crawl products from a specific category"""
        logger.info(f"Crawling products from category: {category_url}")
        
        try:
            products_crawled = 0
            current_page = 1
            
            while (current_page <= self.max_pages_per_category and 
                   products_crawled < self.max_products):
                
                # Build page URL (assuming pagination pattern)
                if current_page == 1:
                    page_url = category_url
                else:
                    page_url = f"{category_url}?page={current_page}"
                
                # Fetch listing page
                listing_html = await self.fetch_url(page_url)
                if not listing_html:
                    break
                
                # Parse product links
                product_links = self.listing_parser.extract_product_links(
                    listing_html, self.base_url
                )
                
                if not product_links:
                    logger.info(f"No products found on page {current_page}")
                    break
                
                logger.info(f"Found {len(product_links)} products on page {current_page}")
                
                # Crawl products with concurrency control
                semaphore = asyncio.Semaphore(self.concurrency)
                tasks = []
                
                for product_url in product_links:
                    if products_crawled >= self.max_products:
                        break
                    
                    if product_url in self.crawled_urls:
                        continue
                    
                    task = self._crawl_single_product(semaphore, product_url)
                    tasks.append(task)
                    self.crawled_urls.add(product_url)
                
                # Execute product crawl tasks
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Count successful crawls
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"Product crawl error: {result}")
                    elif result:
                        products_crawled += 1
                
                current_page += 1
                
                # Check for next page
                has_next = self.listing_parser.has_next_page(listing_html)
                if not has_next:
                    logger.info("No more pages found")
                    break
            
            self.stats["products_crawled"] = products_crawled
            logger.info(f"Category crawl completed. Crawled {products_crawled} products")
            
            return self.stats
            
        except Exception as e:
            logger.error(f"Category product crawl failed: {e}")
            raise
    
    async def _crawl_single_product(self, semaphore: asyncio.Semaphore, product_url: str) -> bool:
        """Crawl a single product with semaphore control"""
        async with semaphore:
            try:
                # Fetch product page
                product_html = await self.fetch_url(product_url)
                if not product_html:
                    return False
                
                # Parse product data
                product_data = self.product_parser.parse_product(product_html, product_url)
                if not product_data:
                    logger.warning(f"No product data extracted from {product_url}")
                    return False
                
                # Save to database
                with get_session_context() as session:
                    # Check if product exists
                    existing = session.query(Product).filter(Product.url == product_url).first()
                    if existing:
                        # Update existing product
                        for key, value in product_data.items():
                            if hasattr(existing, key) and value is not None:
                                setattr(existing, key, value)
                        existing.last_seen_at = product_data.get("crawled_at")
                    else:
                        # Create new product
                        product = Product(**product_data)
                        session.add(product)
                
                logger.info(f"Saved product: {product_data.get('name', '')[:50]}...")
                return True
                
            except Exception as e:
                logger.error(f"Error crawling product {product_url}: {e}")
                self.stats["errors"].append({"url": product_url, "error": str(e)})
                return False
    
    async def crawl_all_products(self) -> Dict[str, Any]:
        """Crawl products from all categories"""
        logger.info("Starting full product crawl...")
        
        try:
            with get_session_context() as session:
                categories = session.query(Category).filter(Category.is_active == True).all()
            
            if not categories:
                raise Exception("No categories found. Run crawl-categories first.")
            
            logger.info(f"Found {len(categories)} categories to crawl")
            
            total_products = 0
            
            for category in categories:
                if total_products >= self.max_products:
                    break
                
                logger.info(f"Crawling category: {category.name}")
                
                # Set remaining product limit for this category
                remaining = self.max_products - total_products
                old_max = self.max_products
                self.max_products = remaining
                
                # Crawl category
                result = await self.crawl_category_products(category.url)
                
                # Restore original limit
                self.max_products = old_max
                
                total_products += result.get("products_crawled", 0)
                
                logger.info(f"Category {category.name} completed. "
                           f"Total products: {total_products}")
            
            self.stats["products_crawled"] = total_products
            
            return self.stats
            
        except Exception as e:
            logger.error(f"Full product crawl failed: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.client:
            await self.client.aclose()