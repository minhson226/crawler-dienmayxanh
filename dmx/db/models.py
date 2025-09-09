"""
Database models using SQLAlchemy ORM
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, 
    Float, Boolean, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped

Base = declarative_base()


class Category(Base):
    """Category model for product categories"""
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    url = Column(String(500), unique=True, nullable=False)
    canonical_url = Column(String(500))
    slug = Column(String(255))
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    breadcrumb_path = Column(Text)  # JSON string of breadcrumb path
    level = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parent = relationship("Category", remote_side=[id])
    children = relationship("Category")
    products = relationship("Product", back_populates="category")
    
    # Indexes
    __table_args__ = (
        Index("idx_category_url", "url"),
        Index("idx_category_slug", "slug"),
        Index("idx_category_parent", "parent_id"),
    )

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"


class Product(Base):
    """Main product model"""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True)
    url = Column(String(500), unique=True, nullable=False)
    canonical_url = Column(String(500))
    slug = Column(String(255))
    product_code = Column(String(100))  # SKU/Product Code
    name = Column(String(500), nullable=False)
    brand = Column(String(100))
    model = Column(String(255))
    category_id = Column(Integer, ForeignKey("categories.id"))
    category_path = Column(Text)  # Text representation of category path
    
    # Product details
    short_desc = Column(Text)
    full_desc_html = Column(Text)
    availability = Column(String(50))
    warranty_info = Column(String(255))
    shipping_info = Column(String(255))
    
    # Pricing
    price_regular = Column(Float)
    price_promo = Column(Float)
    discount_percent = Column(Float)
    
    # Ratings & Reviews
    rating_avg = Column(Float)
    rating_count = Column(Integer, default=0)
    review_count = Column(Integer, default=0)
    
    # SEO
    meta_title = Column(String(255))
    meta_desc = Column(Text)
    
    # Tracking
    hash_content = Column(String(64))  # MD5 hash for change detection
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    crawled_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    category = relationship("Category", back_populates="products")
    specifications = relationship("ProductSpec", back_populates="product", cascade="all, delete-orphan")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_product_url", "url"),
        Index("idx_product_code", "product_code"),
        Index("idx_product_brand", "brand"),
        Index("idx_product_category", "category_id"),
        Index("idx_product_crawled", "crawled_at"),
        Index("idx_product_name", "name"),
    )

    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', code='{self.product_code}')>"


class ProductSpec(Base):
    """Product specifications/attributes"""
    __tablename__ = "product_specs"
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    spec_key = Column(String(255), nullable=False)
    spec_value = Column(Text)
    spec_group = Column(String(255))  # Group like "Display", "Camera", etc.
    position = Column(Integer, default=0)
    
    # Relationships
    product = relationship("Product", back_populates="specifications")
    
    # Indexes
    __table_args__ = (
        Index("idx_spec_product", "product_id"),
        Index("idx_spec_key", "spec_key"),
        Index("idx_spec_group", "spec_group"),
        UniqueConstraint("product_id", "spec_key", name="uq_product_spec"),
    )

    def __repr__(self):
        return f"<ProductSpec(product_id={self.product_id}, key='{self.spec_key}', value='{self.spec_value}')>"


class ProductImage(Base):
    """Product images"""
    __tablename__ = "product_images"
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    image_url = Column(String(500), nullable=False)
    position = Column(Integer, default=0)
    alt = Column(String(255))
    is_primary = Column(Boolean, default=False)
    
    # Relationships
    product = relationship("Product", back_populates="images")
    
    # Indexes
    __table_args__ = (
        Index("idx_image_product", "product_id"),
        Index("idx_image_position", "position"),
    )

    def __repr__(self):
        return f"<ProductImage(product_id={self.product_id}, url='{self.image_url}')>"


# Optional extended models for future use
class PriceHistory(Base):
    """Price history tracking"""
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    price_regular = Column(Float)
    price_promo = Column(Float)
    discount_percent = Column(Float)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product")
    
    # Indexes
    __table_args__ = (
        Index("idx_price_product", "product_id"),
        Index("idx_price_recorded", "recorded_at"),
    )


class CrawlLog(Base):
    """Crawl session logs"""
    __tablename__ = "crawl_logs"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(64), nullable=False)
    url = Column(String(500), nullable=False)
    status_code = Column(Integer)
    response_time = Column(Float)
    error_message = Column(Text)
    crawled_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_log_session", "session_id"),
        Index("idx_log_url", "url"),
        Index("idx_log_crawled", "crawled_at"),
    )