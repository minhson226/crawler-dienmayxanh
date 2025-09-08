#!/usr/bin/env python3
"""
Script to analyze HTML structure and generate selectors.yaml
"""
import os
import re
import yaml
from pathlib import Path
from selectolax.parser import HTMLParser

def analyze_html_files():
    """Analyze HTML files to extract selector patterns"""
    html_dir = Path("html_structure")
    selectors = {
        "home": {
            "category_links": [],
            "navigation_menu": []
        },
        "category": {
            "breadcrumb": [],
            "product_cards": [],
            "next_page": [],
            "product_links": []
        },
        "product_detail": {
            "name": [],
            "price_regular": [],
            "price_promo": [],
            "price_old": [],
            "discount_percent": [],
            "brand": [],
            "category_path": [],
            "specifications": [],
            "specs_group": [],
            "specs_kv": [],
            "gallery_images": [],
            "description": [],
            "rating": [],
            "availability": [],
            "product_code": []
        }
    }
    
    # Analyze home page
    home_file = html_dir / "index.html"
    if home_file.exists():
        with open(home_file, 'r', encoding='utf-8') as f:
            html = f.read()
            parser = HTMLParser(html)
            
            # Look for category links
            main_menu = parser.css_first(".main-menu-categories, .list-cates, .gr-cates")
            if main_menu:
                selectors["home"]["category_links"].extend([
                    ".main-menu-categories a[href]",
                    ".list-cates a[href]", 
                    ".gr-cates a[href]",
                    ".cate-item a[href]"
                ])
            
            # Navigation menu
            selectors["home"]["navigation_menu"].extend([
                ".main-menu a",
                ".main-menu-header a",
                "nav a[href]"
            ])
    
    # Analyze category pages
    for category_file in html_dir.glob("*.html"):
        if category_file.name in ["index.html"]:
            continue
            
        with open(category_file, 'r', encoding='utf-8') as f:
            html = f.read()
            parser = HTMLParser(html)
            
            # Check if this looks like a category listing page
            listproduct = parser.css_first(".listproduct")
            if listproduct:
                # Product cards
                selectors["category"]["product_cards"].extend([
                    ".listproduct .item",
                    ".listproduct .item a",
                    ".product-item"
                ])
                
                # Product links  
                selectors["category"]["product_links"].extend([
                    ".listproduct .item a[href]",
                    ".item-img a[href]",
                    "h3 a[href]"
                ])
                
                # Pagination
                selectors["category"]["next_page"].extend([
                    "a.next",
                    "a[rel='next']",
                    ".pagination .next",
                    ".paging a.next"
                ])
            
            # Breadcrumb
            breadcrumb = parser.css_first(".breadcrumb")
            if breadcrumb:
                selectors["category"]["breadcrumb"].extend([
                    ".breadcrumb",
                    ".breadcrumb li",
                    "nav.breadcrumb"
                ])
    
    # Analyze product detail pages
    for product_file in html_dir.rglob("*/*.html"):
        with open(product_file, 'r', encoding='utf-8') as f:
            html = f.read()
            parser = HTMLParser(html)
            
            # Look for product detail indicators
            h1 = parser.css_first("h1")
            price = parser.css_first(".price, .box-price-present")
            
            if h1 and price:
                # Product name
                selectors["product_detail"]["name"].extend([
                    "h1",
                    ".product-name",
                    ".detail-title h1"
                ])
                
                # Prices
                selectors["product_detail"]["price_regular"].extend([
                    ".price",
                    ".box-price-present", 
                    ".price-current",
                    ".price-regular"
                ])
                
                selectors["product_detail"]["price_promo"].extend([
                    ".price-sale",
                    ".price-promo",
                    ".box-price-present"
                ])
                
                selectors["product_detail"]["price_old"].extend([
                    ".price-old",
                    ".box-price-old",
                    ".price-before"
                ])
                
                selectors["product_detail"]["discount_percent"].extend([
                    ".percent",
                    ".box-price-percent",
                    ".discount-percent"
                ])
                
                # Specifications
                specs = parser.css_first(".parameter, .specs, .specifications")
                if specs:
                    selectors["product_detail"]["specifications"].extend([
                        ".parameter",
                        ".specifications",
                        ".specs",
                        ".parameter__list"
                    ])
                    
                    selectors["product_detail"]["specs_kv"].extend([
                        ".parameter__list li",
                        ".specs tr",
                        ".spec-item"
                    ])
                
                # Images
                selectors["product_detail"]["gallery_images"].extend([
                    ".gallery img",
                    ".product-images img",
                    ".box01__show img",
                    ".item-img img"
                ])
                
                # Brand and category
                selectors["product_detail"]["brand"].extend([
                    "[data-brand]",
                    ".brand",
                    "a[href*='brand']"
                ])
                
                # Rating
                selectors["product_detail"]["rating"].extend([
                    ".rating",
                    ".rating-star",
                    ".vote-txt"
                ])
    
    # Remove duplicates and empty entries
    def clean_selectors(obj):
        if isinstance(obj, dict):
            return {k: clean_selectors(v) for k, v in obj.items() if v}
        elif isinstance(obj, list):
            return list(dict.fromkeys([s for s in obj if s]))  # Remove duplicates
        return obj
    
    return clean_selectors(selectors)

def main():
    """Main function"""
    print("Analyzing HTML structure...")
    selectors = analyze_html_files()
    
    # Save to YAML
    output_file = Path("configs/selectors.yaml")
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(selectors, f, default_flow_style=False, allow_unicode=True, indent=2)
    
    print(f"Selectors saved to {output_file}")
    print("\nGenerated selectors preview:")
    print(yaml.dump(selectors, default_flow_style=False, allow_unicode=True, indent=2))

if __name__ == "__main__":
    main()