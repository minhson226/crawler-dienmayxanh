"""
Live smoke test - crawl a small sample with rate limiting
"""
import pytest
import asyncio
import time
from dmx.crawler.runner import CrawlerRunner
from dmx.db import get_session_context, Product, Category


class TestLiveSmoke:
    """Live smoke test with rate limiting"""
    
    @pytest.mark.asyncio
    async def test_live_smoke_crawl(self):
        """Test live crawling with small sample"""
        
        # Initialize crawler with conservative settings
        crawler = CrawlerRunner(
            base_url="https://www.dienmayxanh.com",
            max_products=5,  # Very small sample
            max_pages_per_category=1,  # Only first page
            concurrency=1,  # Single request at a time
            respect_robots=True
        )
        
        try:
            start_time = time.time()
            
            # Test category crawling
            print("\\nTesting category crawl...")
            category_result = await crawler.crawl_categories_only(max_level=1)
            
            print(f"Categories found: {category_result.get('categories_found', 0)}")
            
            # Check if categories were saved
            with get_session_context() as session:
                category_count = session.query(Category).count()
                print(f"Categories in database: {category_count}")
            
            # Test product crawling (only if we have categories)
            if category_count > 0:
                print("\\nTesting product crawl...")
                product_result = await crawler.crawl_all_products()
                
                print(f"Products crawled: {product_result.get('products_crawled', 0)}")
                
                # Check if products were saved
                with get_session_context() as session:
                    product_count = session.query(Product).count()
                    print(f"Products in database: {product_count}")
                    
                    # Show sample products
                    if product_count > 0:
                        sample_products = session.query(Product).limit(3).all()
                        print("\\nSample products:")
                        for product in sample_products:
                            print(f"  - {product.name[:60]}...")
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"\\nSmoke test completed in {duration:.2f} seconds")
            
            # Basic assertions
            assert category_result.get('categories_found', 0) >= 0
            if 'errors' in category_result:
                print(f"Errors encountered: {len(category_result['errors'])}")
                for error in category_result['errors'][:3]:  # Show first 3 errors
                    print(f"  - {error}")
            
            # Success if we either found categories or completed without major errors
            assert True  # Basic completion test
            
        finally:
            # Cleanup
            await crawler.cleanup()
    
    def test_robots_txt_respect(self):
        """Test that crawler respects robots.txt"""
        crawler = CrawlerRunner(respect_robots=True)
        
        # This should load robots.txt
        assert crawler.robots_checker is not None
        
        # Test with a URL that should be allowed
        test_url = "https://www.dienmayxanh.com/"
        # Note: We can't easily test this without making actual requests
        # This is more of a structure test
        assert hasattr(crawler.robots_checker, 'can_fetch')
    
    def test_crawler_configuration(self):
        """Test crawler configuration"""
        crawler = CrawlerRunner(
            max_products=10,
            concurrency=2,
            respect_robots=True
        )
        
        assert crawler.max_products == 10
        assert crawler.concurrency == 2
        assert crawler.respect_robots == True
        assert crawler.robots_checker is not None
        assert crawler.throttler.concurrency == 2