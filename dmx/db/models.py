"""Database models for DMX Crawler."""

import hashlib
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, Boolean, 
    ForeignKey, Index, UniqueConstraint, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.sql import func

Base = declarative_base()


class Category(Base):
    """Product category model."""
    
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False, unique=True)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    breadcrumb_path = Column(Text, nullable=True)
    level = Column(Integer, default=1)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    parent = relationship("Category", remote_side=[id], backref="children")
    products = relationship("Product", back_populates="category")
    
    # Indexes
    __table_args__ = (
        Index("idx_category_url", "url"),
        Index("idx_category_parent", "parent_id"),
        Index("idx_category_level", "level"),
    )
    
    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}', level={self.level})>"


class Product(Base):
    """Product model."""
    
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # URLs and identifiers
    url = Column(String(500), nullable=False)
    canonical_url = Column(String(500), nullable=True)
    slug = Column(String(255), nullable=True)
    product_code = Column(String(100), nullable=True)  # SKU
    
    # Basic product info
    name = Column(String(500), nullable=False)
    brand = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    category_path = Column(Text, nullable=True)  # Breadcrumb text
    
    # Descriptions
    short_desc = Column(Text, nullable=True)
    full_desc_html = Column(Text, nullable=True)
    
    # Availability and logistics
    availability = Column(String(50), default="unknown")  # in_stock, out_of_stock, pre_order
    warranty_info = Column(Text, nullable=True)
    shipping_info = Column(Text, nullable=True)
    
    # Ratings and reviews
    rating_avg = Column(Float, nullable=True)
    rating_count = Column(Integer, default=0)
    review_count = Column(Integer, default=0)
    
    # Pricing
    price_regular = Column(Float, nullable=True)  # Original price
    price_promo = Column(Float, nullable=True)    # Sale price
    discount_percent = Column(Float, nullable=True)
    
    # SEO and meta
    meta_title = Column(String(500), nullable=True)
    meta_desc = Column(Text, nullable=True)
    
    # Data integrity
    hash_content = Column(String(64), nullable=True)  # SHA256 of content for change detection
    
    # Timestamps
    first_seen_at = Column(DateTime, default=func.now())
    last_seen_at = Column(DateTime, default=func.now())
    crawled_at = Column(DateTime, default=func.now())
    
    # Relationships
    category = relationship("Category", back_populates="products")
    specifications = relationship("ProductSpec", back_populates="product", cascade="all, delete-orphan")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    
    # Indexes and constraints
    __table_args__ = (
        Index("idx_product_url", "url"),
        Index("idx_product_canonical", "canonical_url"),
        Index("idx_product_code", "product_code"),
        Index("idx_product_name", "name"),
        Index("idx_product_brand", "brand"),
        Index("idx_product_category", "category_id"),
        Index("idx_product_price_promo", "price_promo"),
        Index("idx_product_crawled", "crawled_at"),
        UniqueConstraint("url", name="uq_product_url"),
    )
    
    def generate_content_hash(self) -> str:
        """Generate hash of product content for change detection."""
        content = f"{self.name}|{self.price_promo}|{self.price_regular}|{self.short_desc}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def update_hash(self) -> None:
        """Update content hash."""
        self.hash_content = self.generate_content_hash()
    
    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name='{self.name[:50]}...', price={self.price_promo})>"


class ProductSpec(Base):
    """Product specifications model."""
    
    __tablename__ = "product_specs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    spec_key = Column(String(200), nullable=False)    # e.g., "Màn hình"
    spec_value = Column(Text, nullable=False)         # e.g., "55 inch, 4K UHD"
    spec_group = Column(String(100), nullable=True)  # e.g., "Thông số kỹ thuật"
    
    # Ordering within group
    sort_order = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    product = relationship("Product", back_populates="specifications")
    
    # Indexes
    __table_args__ = (
        Index("idx_spec_product", "product_id"),
        Index("idx_spec_key", "spec_key"),
        Index("idx_spec_group", "spec_group"),
        UniqueConstraint("product_id", "spec_key", name="uq_product_spec"),
    )
    
    def __repr__(self) -> str:
        return f"<ProductSpec(product_id={self.product_id}, key='{self.spec_key}', value='{self.spec_value[:30]}...')>"


class ProductImage(Base):
    """Product images model."""
    
    __tablename__ = "product_images"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    image_url = Column(String(1000), nullable=False)
    alt_text = Column(String(500), nullable=True)
    position = Column(Integer, default=0)  # 0 = main image
    
    # Image metadata
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    file_size = Column(Integer, nullable=True)
    
    # Local storage (if enabled)
    local_path = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    product = relationship("Product", back_populates="images")
    
    # Indexes
    __table_args__ = (
        Index("idx_image_product", "product_id"),
        Index("idx_image_position", "position"),
    )
    
    def __repr__(self) -> str:
        return f"<ProductImage(product_id={self.product_id}, position={self.position}, url='{self.image_url[:50]}...')>"


class ProductVariant(Base):
    """Product variants model (color, size, etc.)."""
    
    __tablename__ = "product_variants"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    variant_type = Column(String(50), nullable=False)  # color, size, storage, etc.
    variant_value = Column(String(200), nullable=False)
    variant_sku = Column(String(100), nullable=True)
    
    # Variant-specific pricing
    price_modifier = Column(Float, default=0.0)  # Price difference from base product
    availability = Column(String(50), default="unknown")
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    product = relationship("Product", back_populates="variants")
    
    # Indexes
    __table_args__ = (
        Index("idx_variant_product", "product_id"),
        Index("idx_variant_type", "variant_type"),
        UniqueConstraint("product_id", "variant_type", "variant_value", name="uq_product_variant"),
    )
    
    def __repr__(self) -> str:
        return f"<ProductVariant(product_id={self.product_id}, type='{self.variant_type}', value='{self.variant_value}')>"


class CrawlSession(Base):
    """Crawl session tracking."""
    
    __tablename__ = "crawl_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_name = Column(String(200), nullable=False)
    status = Column(String(50), default="running")  # running, completed, failed, paused
    
    # Configuration snapshot
    config_snapshot = Column(JSON, nullable=True)
    
    # Progress tracking
    urls_discovered = Column(Integer, default=0)
    urls_crawled = Column(Integer, default=0)
    products_saved = Column(Integer, default=0)
    categories_saved = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    
    # Timing
    started_at = Column(DateTime, default=func.now())
    finished_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Error tracking
    last_error = Column(Text, nullable=True)
    
    # Checkpoint data
    checkpoint_data = Column(JSON, nullable=True)
    
    def __repr__(self) -> str:
        return f"<CrawlSession(id={self.id}, name='{self.session_name}', status='{self.status}')>"


class CrawlError(Base):
    """Crawl error tracking."""
    
    __tablename__ = "crawl_errors"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("crawl_sessions.id"), nullable=True)
    
    url = Column(String(500), nullable=False)
    error_type = Column(String(100), nullable=False)  # http_error, parse_error, timeout, etc.
    error_message = Column(Text, nullable=False)
    error_details = Column(JSON, nullable=True)  # Stack trace, response data, etc.
    
    retry_count = Column(Integer, default=0)
    resolved = Column(Boolean, default=False)
    
    # Timestamps
    occurred_at = Column(DateTime, default=func.now())
    resolved_at = Column(DateTime, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_error_session", "session_id"),
        Index("idx_error_url", "url"),
        Index("idx_error_type", "error_type"),
        Index("idx_error_occurred", "occurred_at"),
    )
    
    def __repr__(self) -> str:
        return f"<CrawlError(url='{self.url}', type='{self.error_type}', resolved={self.resolved})>"


# Optional: Store availability model for different locations
class StoreAvailability(Base):
    """Store availability model (optional extension)."""
    
    __tablename__ = "store_availability"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    store_name = Column(String(200), nullable=False)
    store_location = Column(String(500), nullable=True)
    store_code = Column(String(50), nullable=True)
    
    availability = Column(String(50), default="unknown")  # in_stock, out_of_stock, limited
    quantity = Column(Integer, nullable=True)
    last_updated = Column(DateTime, default=func.now())
    
    # Relationships
    product = relationship("Product")
    
    # Indexes
    __table_args__ = (
        Index("idx_store_product", "product_id"),
        Index("idx_store_name", "store_name"),
        UniqueConstraint("product_id", "store_code", name="uq_product_store"),
    )


# Optional: Price history model
class PriceHistory(Base):
    """Price history tracking (optional extension)."""
    
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    price_regular = Column(Float, nullable=True)
    price_promo = Column(Float, nullable=True)
    discount_percent = Column(Float, nullable=True)
    
    # Timestamps
    recorded_at = Column(DateTime, default=func.now())
    
    # Relationships
    product = relationship("Product")
    
    # Indexes
    __table_args__ = (
        Index("idx_price_product", "product_id"),
        Index("idx_price_recorded", "recorded_at"),
    )