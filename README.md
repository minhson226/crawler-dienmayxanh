# DMX Crawler - Production-Grade Crawler for dienmayxanh.com

A production-ready web crawler for extracting product data from dienmayxanh.com, built with modern Python tools and best practices.

## Features

- **Config-driven architecture** with YAML selectors and settings
- **Respects robots.txt** and implements proper rate limiting  
- **SQLAlchemy ORM** with SQLite (default) and PostgreSQL support
- **Playwright + HTTP** hybrid approach for static/dynamic content
- **Complete CLI interface** for all operations
- **Comprehensive testing** (unit, integration, live smoke tests)
- **Production-ready** error handling, logging, and checkpointing
- **Idempotent operations** with deduplication

## Quick Start

### Installation

```bash
# Using Poetry (recommended)
poetry install
poetry shell

# Or using pip
pip install -r requirements.txt
```

### Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
# DB_URL=sqlite:///dmx.sqlite  # Default SQLite
# DB_URL=postgresql+psycopg://user:pass@host/db  # For PostgreSQL
```

### Initialize Database

```bash
python -m dmx.main init-db
```

### Run Crawler

```bash
# Full crawl with limits
python -m dmx.main crawl-all --max-products 200 --concurrency 3

# Categories only  
python -m dmx.main crawl-categories --limit-level 2

# Export data
python -m dmx.main export --format csv --out products.csv
```

## Architecture

### Project Structure

```
dmx_crawler/
├── configs/
│   ├── config.yaml           # Base configuration
│   └── selectors.yaml         # CSS/XPath selectors
├── dmx/
│   ├── main.py               # CLI interface  
│   ├── crawler/              # Core crawling logic
│   ├── parsers/              # HTML parsing modules
│   ├── db/                   # Database models & session
│   └── utils/                # Utilities & helpers
├── tests/                    # Comprehensive test suite
├── html_structure/           # Offline HTML fixtures
└── scripts/                  # Helper scripts
```

### Database Schema

```mermaid
erDiagram
    products {
        int id PK
        string url UK
        string canonical_url
        string slug
        string product_code
        string name
        string brand
        string model
        text category_path
        text short_desc
        text full_desc_html
        string availability
        text warranty_info
        text shipping_info
        float rating_avg
        int rating_count
        int review_count
        decimal price_regular
        decimal price_promo
        float discount_percent
        string meta_title
        text meta_desc
        string hash_content
        datetime first_seen_at
        datetime last_seen_at
        datetime crawled_at
    }

    categories {
        int id PK
        string name
        string url UK
        int parent_id FK
        text breadcrumb_path
    }

    product_specs {
        int id PK
        int product_id FK
        string spec_key
        text spec_value
        string spec_group
    }

    product_images {
        int id PK
        int product_id FK
        string image_url
        int position
        string alt
    }

    products ||--o{ product_specs : has
    products ||--o{ product_images : has
    categories ||--o{ categories : parent
```

## Configuration

### config.yaml
```yaml
base_url: "https://www.dienmayxanh.com/"
user_agent: "DMX-Crawler/1.0"
robots_check: true
concurrency: 3
delay_range: [1, 3]  # Random delay in seconds
max_products: 0      # 0 = unlimited
use_playwright: "auto"  # auto/static/always
```

### selectors.yaml  
```yaml
home:
  category_links: ["nav a[href*='/']", ".menu a"]
category:
  breadcrumb: ["nav.breadcrumb", "ul.breadcrumb"]
  product_card_links: [".listproduct .item a", ".product-item a"]
  next_page: ["a.paging__next", "a[rel='next']"]
product_detail:
  name: ["h1", "h1.product-name"]
  price_regular: ["span.price-old", ".original-price"]
  price_promo: ["span.price-current", ".sale-price"]
  # ... additional selectors
```

## CLI Commands

| Command | Description | Example |
|---------|-------------|---------|
| `init-db` | Initialize database schema | `python -m dmx.main init-db` |
| `crawl-all` | Full crawl with options | `python -m dmx.main crawl-all --max-products 100` |
| `crawl-categories` | Categories only | `python -m dmx.main crawl-categories` |
| `crawl-products` | Products from URLs | `python -m dmx.main crawl-products --urls urls.txt` |
| `resume` | Resume interrupted crawl | `python -m dmx.main resume` |
| `export` | Export data | `python -m dmx.main export --format json` |

## Testing

```bash
# Unit tests (offline HTML)
pytest tests/unit/ -v

# Integration tests (mocked)  
pytest tests/integration/ -v

# Live smoke test (respects robots.txt)
pytest tests/live/ -v --live

# All tests with coverage
pytest --cov=dmx --cov-report=html
```

## Legal & Ethics

- **Respects robots.txt** - Checks and follows robots.txt rules
- **Rate limiting** - Implements delays and concurrency limits  
- **User-Agent** - Identifies crawler transparently
- **Scope limitation** - Only crawls product data for legitimate purposes
- **No aggressive crawling** - Reasonable delays between requests

## Extending to Other Sites

The architecture is designed to be extensible:

1. Create new selector configs in `configs/`
2. Extend parsers in `dmx/parsers/`  
3. Update database models if needed
4. Add site-specific rate limiting rules

## Development

```bash
# Setup development environment
poetry install --with dev
pre-commit install

# Code formatting
black dmx/ tests/
ruff dmx/ tests/

# Type checking  
mypy dmx/

# Run full test suite
pytest
```

## License

This project is for educational and legitimate business use only. Please ensure compliance with the target website's terms of service and applicable laws.