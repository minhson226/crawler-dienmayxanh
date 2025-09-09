"""
Export utilities for crawled data
"""
import csv
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import joinedload

from dmx.db import get_session_context, Product, Category, ProductSpec, ProductImage

logger = logging.getLogger(__name__)


def export_products(
    output_path: Path,
    format: str = "csv",
    limit: Optional[int] = None,
    category_filter: Optional[str] = None
) -> int:
    """
    Export products to CSV or JSON
    
    Args:
        output_path: Output file path
        format: Export format ("csv" or "json")
        limit: Limit number of records
        category_filter: Filter by category name
        
    Returns:
        Number of records exported
    """
    try:
        with get_session_context() as session:
            # Build query
            query = session.query(Product).options(
                joinedload(Product.category),
                joinedload(Product.specifications),
                joinedload(Product.images)
            )
            
            # Apply category filter
            if category_filter:
                query = query.join(Category).filter(
                    Category.name.ilike(f"%{category_filter}%")
                )
            
            # Order by crawled date
            query = query.order_by(Product.crawled_at.desc())
            
            # Apply limit
            if limit:
                query = query.limit(limit)
            
            products = query.all()
        
        if not products:
            logger.warning("No products found to export")
            return 0
        
        # Export based on format
        if format.lower() == "csv":
            return _export_csv(products, output_path)
        elif format.lower() == "json":
            return _export_json(products, output_path)
        else:
            raise ValueError(f"Unsupported format: {format}")
            
    except Exception as e:
        logger.error(f"Error exporting products: {e}")
        raise


def _export_csv(products: List[Product], output_path: Path) -> int:
    """Export products to CSV"""
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'id', 'name', 'brand', 'model', 'product_code', 'url',
                'category_name', 'category_path', 'price_regular', 'price_promo',
                'discount_percent', 'availability', 'warranty_info',
                'rating_avg', 'review_count', 'short_desc', 'specifications',
                'image_urls', 'crawled_at'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for product in products:
                # Prepare specifications
                specs_text = "; ".join([
                    f"{spec.spec_key}: {spec.spec_value}"
                    for spec in product.specifications
                ])
                
                # Prepare image URLs
                image_urls = "; ".join([img.image_url for img in product.images])
                
                writer.writerow({
                    'id': product.id,
                    'name': product.name,
                    'brand': product.brand or '',
                    'model': product.model or '',
                    'product_code': product.product_code or '',
                    'url': product.url,
                    'category_name': product.category.name if product.category else '',
                    'category_path': product.category_path or '',
                    'price_regular': product.price_regular,
                    'price_promo': product.price_promo,
                    'discount_percent': product.discount_percent,
                    'availability': product.availability or '',
                    'warranty_info': product.warranty_info or '',
                    'rating_avg': product.rating_avg,
                    'review_count': product.review_count,
                    'short_desc': product.short_desc or '',
                    'specifications': specs_text,
                    'image_urls': image_urls,
                    'crawled_at': product.crawled_at.isoformat() if product.crawled_at else ''
                })
        
        logger.info(f"Exported {len(products)} products to CSV: {output_path}")
        return len(products)
        
    except Exception as e:
        logger.error(f"Error exporting to CSV: {e}")
        raise


def _export_json(products: List[Product], output_path: Path) -> int:
    """Export products to JSON"""
    try:
        products_data = []
        
        for product in products:
            # Convert product to dict
            product_dict = {
                'id': product.id,
                'name': product.name,
                'brand': product.brand,
                'model': product.model,
                'product_code': product.product_code,
                'url': product.url,
                'canonical_url': product.canonical_url,
                'slug': product.slug,
                'category': {
                    'id': product.category.id if product.category else None,
                    'name': product.category.name if product.category else None,
                    'url': product.category.url if product.category else None
                } if product.category else None,
                'category_path': product.category_path,
                'pricing': {
                    'price_regular': product.price_regular,
                    'price_promo': product.price_promo,
                    'discount_percent': product.discount_percent
                },
                'descriptions': {
                    'short_desc': product.short_desc,
                    'full_desc_html': product.full_desc_html
                },
                'availability': product.availability,
                'warranty_info': product.warranty_info,
                'shipping_info': product.shipping_info,
                'rating': {
                    'rating_avg': product.rating_avg,
                    'rating_count': product.rating_count,
                    'review_count': product.review_count
                },
                'seo': {
                    'meta_title': product.meta_title,
                    'meta_desc': product.meta_desc
                },
                'specifications': [
                    {
                        'key': spec.spec_key,
                        'value': spec.spec_value,
                        'group': spec.spec_group
                    }
                    for spec in product.specifications
                ],
                'images': [
                    {
                        'url': img.image_url,
                        'alt': img.alt,
                        'position': img.position,
                        'is_primary': img.is_primary
                    }
                    for img in product.images
                ],
                'timestamps': {
                    'first_seen_at': product.first_seen_at.isoformat() if product.first_seen_at else None,
                    'last_seen_at': product.last_seen_at.isoformat() if product.last_seen_at else None,
                    'crawled_at': product.crawled_at.isoformat() if product.crawled_at else None
                }
            }
            
            products_data.append(product_dict)
        
        # Write JSON file
        with open(output_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(products_data, jsonfile, ensure_ascii=False, indent=2)
        
        logger.info(f"Exported {len(products)} products to JSON: {output_path}")
        return len(products)
        
    except Exception as e:
        logger.error(f"Error exporting to JSON: {e}")
        raise


def export_categories(output_path: Path, format: str = "csv") -> int:
    """Export categories to file"""
    try:
        with get_session_context() as session:
            categories = session.query(Category).order_by(Category.level, Category.name).all()
        
        if not categories:
            logger.warning("No categories found to export")
            return 0
        
        if format.lower() == "csv":
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'id', 'name', 'url', 'slug', 'parent_id', 'level',
                    'breadcrumb_path', 'is_active', 'created_at'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for category in categories:
                    writer.writerow({
                        'id': category.id,
                        'name': category.name,
                        'url': category.url,
                        'slug': category.slug,
                        'parent_id': category.parent_id,
                        'level': category.level,
                        'breadcrumb_path': category.breadcrumb_path,
                        'is_active': category.is_active,
                        'created_at': category.created_at.isoformat() if category.created_at else ''
                    })
        
        elif format.lower() == "json":
            categories_data = [
                {
                    'id': cat.id,
                    'name': cat.name,
                    'url': cat.url,
                    'slug': cat.slug,
                    'parent_id': cat.parent_id,
                    'level': cat.level,
                    'breadcrumb_path': cat.breadcrumb_path,
                    'is_active': cat.is_active,
                    'created_at': cat.created_at.isoformat() if cat.created_at else None
                }
                for cat in categories
            ]
            
            with open(output_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(categories_data, jsonfile, ensure_ascii=False, indent=2)
        
        logger.info(f"Exported {len(categories)} categories to {output_path}")
        return len(categories)
        
    except Exception as e:
        logger.error(f"Error exporting categories: {e}")
        raise