"""Export utilities for products data."""

import csv
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from dmx.db.session import get_session
from dmx.db.models import Product, Category, ProductSpec, ProductImage


def export_products(
    output_file: str,
    format: str = "csv",
    limit: Optional[int] = None,
    include_specs: bool = True,
    include_images: bool = True,
) -> int:
    """Export products to CSV or JSON format."""
    
    if format not in ["csv", "json"]:
        raise ValueError("Format must be 'csv' or 'json'")
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with get_session() as session:
        # Build query
        query = session.query(Product).join(Category, isouter=True)
        
        if limit:
            query = query.limit(limit)
        
        products = query.all()
        
        if format == "csv":
            count = _export_to_csv(products, output_path, include_specs, include_images)
        else:  # json
            count = _export_to_json(products, output_path, include_specs, include_images)
        
        return count


def _export_to_csv(
    products: List[Product],
    output_path: Path,
    include_specs: bool,
    include_images: bool,
) -> int:
    """Export products to CSV format."""
    
    # Define CSV headers
    headers = [
        "id", "name", "brand", "model", "product_code", "url", "canonical_url",
        "category_name", "category_path", "short_desc", "availability",
        "price_regular", "price_promo", "discount_percent",
        "rating_avg", "rating_count", "review_count",
        "warranty_info", "meta_title", "meta_desc",
        "first_seen_at", "last_seen_at", "crawled_at"
    ]
    
    if include_specs:
        headers.extend(["specs_json"])
    
    if include_images:
        headers.extend(["main_image", "all_images_json"])
    
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        
        for product in products:
            row = {
                "id": product.id,
                "name": product.name,
                "brand": product.brand,
                "model": product.model,
                "product_code": product.product_code,
                "url": product.url,
                "canonical_url": product.canonical_url,
                "category_name": product.category.name if product.category else None,
                "category_path": product.category_path,
                "short_desc": product.short_desc,
                "availability": product.availability,
                "price_regular": product.price_regular,
                "price_promo": product.price_promo,
                "discount_percent": product.discount_percent,
                "rating_avg": product.rating_avg,
                "rating_count": product.rating_count,
                "review_count": product.review_count,
                "warranty_info": product.warranty_info,
                "meta_title": product.meta_title,
                "meta_desc": product.meta_desc,
                "first_seen_at": product.first_seen_at.isoformat() if product.first_seen_at else None,
                "last_seen_at": product.last_seen_at.isoformat() if product.last_seen_at else None,
                "crawled_at": product.crawled_at.isoformat() if product.crawled_at else None,
            }
            
            if include_specs:
                specs = {spec.spec_key: spec.spec_value for spec in product.specifications}
                row["specs_json"] = json.dumps(specs, ensure_ascii=False)
            
            if include_images:
                images = [img.image_url for img in product.images]
                row["main_image"] = images[0] if images else None
                row["all_images_json"] = json.dumps(images, ensure_ascii=False)
            
            writer.writerow(row)
    
    return len(products)


def _export_to_json(
    products: List[Product],
    output_path: Path,
    include_specs: bool,
    include_images: bool,
) -> int:
    """Export products to JSON format."""
    
    products_data = []
    
    for product in products:
        product_dict = {
            "id": product.id,
            "name": product.name,
            "brand": product.brand,
            "model": product.model,
            "product_code": product.product_code,
            "url": product.url,
            "canonical_url": product.canonical_url,
            "slug": product.slug,
            "category": {
                "id": product.category.id if product.category else None,
                "name": product.category.name if product.category else None,
                "url": product.category.url if product.category else None,
            },
            "category_path": product.category_path,
            "description": {
                "short": product.short_desc,
                "full_html": product.full_desc_html,
            },
            "availability": product.availability,
            "warranty_info": product.warranty_info,
            "shipping_info": product.shipping_info,
            "pricing": {
                "regular": product.price_regular,
                "promo": product.price_promo,
                "discount_percent": product.discount_percent,
            },
            "ratings": {
                "average": product.rating_avg,
                "count": product.rating_count,
                "review_count": product.review_count,
            },
            "seo": {
                "meta_title": product.meta_title,
                "meta_description": product.meta_desc,
            },
            "timestamps": {
                "first_seen": product.first_seen_at.isoformat() if product.first_seen_at else None,
                "last_seen": product.last_seen_at.isoformat() if product.last_seen_at else None,
                "crawled": product.crawled_at.isoformat() if product.crawled_at else None,
            },
            "hash_content": product.hash_content,
        }
        
        if include_specs:
            specs_by_group = {}
            for spec in product.specifications:
                group = spec.spec_group or "General"
                if group not in specs_by_group:
                    specs_by_group[group] = {}
                specs_by_group[group][spec.spec_key] = spec.spec_value
            
            product_dict["specifications"] = specs_by_group
        
        if include_images:
            images = []
            for img in product.images:
                images.append({
                    "url": img.image_url,
                    "alt": img.alt_text,
                    "position": img.position,
                    "width": img.width,
                    "height": img.height,
                })
            
            product_dict["images"] = images
        
        products_data.append(product_dict)
    
    # Add metadata
    export_data = {
        "metadata": {
            "exported_at": datetime.now().isoformat(),
            "total_products": len(products_data),
            "format_version": "1.0",
            "includes_specs": include_specs,
            "includes_images": include_images,
        },
        "products": products_data,
    }
    
    with open(output_path, 'w', encoding='utf-8') as jsonfile:
        json.dump(export_data, jsonfile, ensure_ascii=False, indent=2)
    
    return len(products)


def export_categories(output_file: str, format: str = "json") -> int:
    """Export categories to JSON or CSV format."""
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with get_session() as session:
        categories = session.query(Category).all()
        
        if format == "csv":
            headers = ["id", "name", "url", "parent_id", "breadcrumb_path", "level", "created_at"]
            
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                
                for category in categories:
                    writer.writerow({
                        "id": category.id,
                        "name": category.name,
                        "url": category.url,
                        "parent_id": category.parent_id,
                        "breadcrumb_path": category.breadcrumb_path,
                        "level": category.level,
                        "created_at": category.created_at.isoformat() if category.created_at else None,
                    })
        
        else:  # json
            categories_data = []
            for category in categories:
                categories_data.append({
                    "id": category.id,
                    "name": category.name,
                    "url": category.url,
                    "parent_id": category.parent_id,
                    "breadcrumb_path": category.breadcrumb_path,
                    "level": category.level,
                    "created_at": category.created_at.isoformat() if category.created_at else None,
                    "children_count": len(category.children),
                    "products_count": len(category.products),
                })
            
            export_data = {
                "metadata": {
                    "exported_at": datetime.now().isoformat(),
                    "total_categories": len(categories_data),
                },
                "categories": categories_data,
            }
            
            with open(output_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(export_data, jsonfile, ensure_ascii=False, indent=2)
        
        return len(categories)


def create_sample_export(output_dir: str = "out", sample_size: int = 10) -> Dict[str, str]:
    """Create sample exports for testing."""
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    files_created = {}
    
    # Sample products CSV
    csv_file = output_path / f"products_sample_{sample_size}.csv"
    count = export_products(str(csv_file), format="csv", limit=sample_size)
    files_created["products_csv"] = str(csv_file)
    
    # Sample products JSON
    json_file = output_path / f"products_sample_{sample_size}.json"
    export_products(str(json_file), format="json", limit=sample_size)
    files_created["products_json"] = str(json_file)
    
    # Categories export
    categories_file = output_path / "categories.json"
    export_categories(str(categories_file), format="json")
    files_created["categories"] = str(categories_file)
    
    return files_created