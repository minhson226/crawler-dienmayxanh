"""
Main CLI application using Typer
"""
import os
import sys
import asyncio
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich import print as rprint
import yaml
from dotenv import load_dotenv

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dmx.db import create_tables, drop_tables, get_session_context
from dmx.crawler.runner import CrawlerRunner
from dmx.utils.export import export_products

# Load environment variables
load_dotenv()

app = typer.Typer(
    name="dmx-cli",
    help="Production-grade crawler for dienmayxanh.com",
    add_completion=False
)
console = Console()


@app.command()
def init_db(
    reset: bool = typer.Option(False, "--reset", help="Drop existing tables first"),
    database_url: Optional[str] = typer.Option(None, "--db-url", help="Database URL")
):
    """Initialize the database and create tables"""
    try:
        if database_url:
            os.environ["DB_URL"] = database_url
            
        if reset:
            console.print("[yellow]Dropping existing tables...[/yellow]")
            drop_tables()
            
        console.print("[blue]Creating database tables...[/blue]")
        create_tables()
        console.print("[green]✓ Database initialized successfully![/green]")
        
    except Exception as e:
        console.print(f"[red]✗ Error initializing database: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def crawl_categories(
    limit_level: int = typer.Option(2, "--limit-level", help="Maximum category depth"),
    max_categories: int = typer.Option(50, "--max-categories", help="Maximum categories to crawl"),
    concurrency: int = typer.Option(3, "--concurrency", help="Concurrent requests"),
    respect_robots: bool = typer.Option(True, "--respect-robots/--ignore-robots", help="Respect robots.txt"),
):
    """Crawl categories only"""
    try:
        runner = CrawlerRunner(
            max_categories=max_categories,
            concurrency=concurrency, 
            respect_robots=respect_robots
        )
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Crawling categories...", total=None)
            
            result = asyncio.run(runner.crawl_categories_only(limit_level))
            
            progress.stop()
            
        console.print(f"[green]✓ Crawled {result['categories_found']} categories[/green]")
        
    except Exception as e:
        console.print(f"[red]✗ Error crawling categories: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def crawl_products(
    category_url: Optional[str] = typer.Option(None, "--category", help="Specific category URL"),
    max_products: int = typer.Option(1000, "--max-products", help="Maximum products to crawl"),
    max_pages: int = typer.Option(50, "--max-pages", help="Maximum pages per category"),
    concurrency: int = typer.Option(3, "--concurrency", help="Concurrent requests"),
    respect_robots: bool = typer.Option(True, "--respect-robots/--ignore-robots", help="Respect robots.txt"),
):
    """Crawl products from categories"""
    try:
        runner = CrawlerRunner(
            max_products=max_products,
            max_pages_per_category=max_pages,
            concurrency=concurrency,
            respect_robots=respect_robots
        )
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Crawling products...", total=None)
            
            if category_url:
                result = asyncio.run(runner.crawl_category_products(category_url))
            else:
                result = asyncio.run(runner.crawl_all_products())
            
            progress.stop()
            
        console.print(f"[green]✓ Crawled {result['products_crawled']} products[/green]")
        if result.get('errors'):
            console.print(f"[yellow]⚠ {len(result['errors'])} errors occurred[/yellow]")
        
    except Exception as e:
        console.print(f"[red]✗ Error crawling products: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def crawl_all(
    max_products: int = typer.Option(1000, "--max-products", help="Maximum products to crawl"),
    max_pages: int = typer.Option(50, "--max-pages", help="Maximum pages per category"),
    concurrency: int = typer.Option(3, "--concurrency", help="Concurrent requests"),
    respect_robots: bool = typer.Option(True, "--respect-robots/--ignore-robots", help="Respect robots.txt"),
    resume: bool = typer.Option(False, "--resume", help="Resume from last crawl session"),
):
    """Crawl everything: categories + products"""
    try:
        runner = CrawlerRunner(
            max_products=max_products,
            max_pages_per_category=max_pages,
            concurrency=concurrency,
            respect_robots=respect_robots
        )
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Crawl categories first
            categories_task = progress.add_task("Crawling categories...", total=None)
            categories_result = asyncio.run(runner.crawl_categories_only())
            progress.stop_task(categories_task)
            
            # Then crawl products
            products_task = progress.add_task("Crawling products...", total=None)
            products_result = asyncio.run(runner.crawl_all_products())
            progress.stop()
            
        # Display results
        table = Table(title="Crawl Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green")
        
        table.add_row("Categories Found", str(categories_result['categories_found']))
        table.add_row("Products Crawled", str(products_result['products_crawled']))
        if products_result.get('errors'):
            table.add_row("Errors", str(len(products_result['errors'])), style="yellow")
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]✗ Error in crawl-all: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def export(
    format: str = typer.Option("csv", "--format", help="Export format (csv, json)"),
    output: str = typer.Option("exports/products.csv", "--out", help="Output file path"),
    limit: int = typer.Option(None, "--limit", help="Limit number of records"),
    category: str = typer.Option(None, "--category", help="Filter by category"),
):
    """Export crawled data to CSV or JSON"""
    try:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Exporting data...", total=None)
            
            count = export_products(
                output_path=output_path,
                format=format,
                limit=limit,
                category_filter=category
            )
            
            progress.stop()
            
        console.print(f"[green]✓ Exported {count} products to {output_path}[/green]")
        
    except Exception as e:
        console.print(f"[red]✗ Error exporting data: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status():
    """Show crawl status and statistics"""
    try:
        with get_session_context() as session:
            from dmx.db.models import Product, Category
            
            product_count = session.query(Product).count()
            category_count = session.query(Category).count()
            
            # Recent products
            recent_products = session.query(Product).order_by(
                Product.crawled_at.desc()
            ).limit(5).all()
            
        # Display status
        table = Table(title="Crawler Status")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Products", str(product_count))
        table.add_row("Total Categories", str(category_count))
        
        console.print(table)
        
        if recent_products:
            console.print("\n[bold]Recent Products:[/bold]")
            for product in recent_products:
                console.print(f"  • {product.name[:60]}...")
                
    except Exception as e:
        console.print(f"[red]✗ Error getting status: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def config():
    """Show current configuration"""
    try:
        # Load config
        config_path = Path("configs/config.yaml")
        if config_path.exists():
            with open(config_path) as f:
                config_data = yaml.safe_load(f)
        else:
            config_data = {}
            
        # Display config
        console.print("[bold]Current Configuration:[/bold]")
        console.print(yaml.dump(config_data, default_flow_style=False))
        
        console.print(f"\n[bold]Environment Variables:[/bold]")
        console.print(f"DB_URL: {os.getenv('DB_URL', 'sqlite:///dmx.sqlite')}")
        console.print(f"BASE_URL: {os.getenv('BASE_URL', 'https://www.dienmayxanh.com')}")
        
    except Exception as e:
        console.print(f"[red]✗ Error showing config: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()