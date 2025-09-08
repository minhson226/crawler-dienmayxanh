"""
Unit tests for selectors using offline HTML files
"""
import pytest
from pathlib import Path
import yaml

from dmx.parsers.home import HomeParser
from dmx.parsers.listing import ListingParser
from dmx.parsers.product_detail import ProductDetailParser


class TestSelectorParsing:
    """Test parsers with offline HTML files"""
    
    @classmethod
    def setup_class(cls):
        """Setup test class"""
        cls.html_dir = Path("html_structure")
        cls.base_url = "https://www.dienmayxanh.com"
        
        # Initialize parsers
        cls.home_parser = HomeParser()
        cls.listing_parser = ListingParser()
        cls.product_parser = ProductDetailParser()
    
    def test_home_page_parsing(self):
        """Test home page category extraction"""
        home_file = self.html_dir / "index.html"
        
        if not home_file.exists():
            pytest.skip("Home page HTML not found")
        
        with open(home_file, 'r', encoding='utf-8') as f:
            html = f.read()
        
        # Extract category links
        category_links = self.home_parser.extract_category_links(html, self.base_url)
        
        # Assertions
        assert len(category_links) > 0, "Should find at least some category links"
        
        for link in category_links[:5]:  # Check first 5
            assert "name" in link
            assert "url" in link
            assert len(link["name"]) > 2
            assert link["url"].startswith("http")
    
    def test_category_listing_parsing(self):
        """Test category listing page parsing"""
        # Find a category listing page
        category_files = list(self.html_dir.glob("*.html"))
        category_files = [f for f in category_files if f.name not in ["index.html"]]
        
        if not category_files:
            pytest.skip("No category HTML files found")
        
        category_file = category_files[0]  # Use first available
        
        with open(category_file, 'r', encoding='utf-8') as f:
            html = f.read()
        
        # Extract product links
        product_links = self.listing_parser.extract_product_links(html, self.base_url)
        
        # Assertions
        assert isinstance(product_links, list)
        
        if product_links:  # If any products found
            for link in product_links[:3]:  # Check first 3
                assert link.startswith("http")
                assert "dienmayxanh.com" in link
    
    def test_product_detail_parsing(self):
        """Test product detail page parsing"""
        # Find product detail pages
        product_files = list(self.html_dir.rglob("*/*.html"))
        
        if not product_files:
            pytest.skip("No product HTML files found")
        
        product_file = product_files[0]  # Use first available
        
        with open(product_file, 'r', encoding='utf-8') as f:
            html = f.read()
        
        # Parse product data
        product_url = f"{self.base_url}/test-product"
        product_data = self.product_parser.parse_product(html, product_url)
        
        # Assertions
        if product_data:  # If parsing succeeded
            assert "name" in product_data
            assert "url" in product_data
            assert product_data["url"] == product_url
            
            # Check for at least some basic fields
            required_fields = ["name", "crawled_at"]
            for field in required_fields:
                assert field in product_data
    
    def test_selectors_config_exists(self):
        """Test that selectors config was generated"""
        config_file = Path("configs/selectors.yaml")
        assert config_file.exists(), "Selectors config should exist"
        
        with open(config_file, 'r', encoding='utf-8') as f:
            selectors = yaml.safe_load(f)
        
        # Check structure
        assert "home" in selectors
        assert "category" in selectors
        assert "product_detail" in selectors
        
        # Check home selectors
        assert "category_links" in selectors["home"]
        assert len(selectors["home"]["category_links"]) > 0
        
        # Check category selectors
        assert "product_links" in selectors["category"]
        assert len(selectors["category"]["product_links"]) > 0
        
        # Check product detail selectors
        assert "name" in selectors["product_detail"]
        assert len(selectors["product_detail"]["name"]) > 0