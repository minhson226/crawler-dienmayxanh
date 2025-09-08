#!/usr/bin/env python3
"""DMX Crawler CLI interface."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from dmx.db.session import init_db, get_session
from dmx.crawler.runner import CrawlerRunner
from dmx.utils.export import export_products
from dmx.db.models import Product, Category

app = typer.Typer(
    name="dmx-cli",
    help="DMX Crawler - Production-grade crawler for dienmayxanh.com",
    rich_markup_mode="rich",
)

console = Console()

def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            RichHandler(console=console, rich_tracebacks=True),
            logging.FileHandler("dmx_crawler.log"),
        ],
    )


@app.command()
def init_db(
    force: bool = typer.Option(False, "--force", "-f", help="Drop existing tables"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Initialize the database with required tables and indexes."""
    setup_logging(verbose)
    
    try:
        console.print("[bold blue]Initializing database...[/]")
        init_db(drop_existing=force)
        console.print("[bold green]✓ Database initialized successfully![/]")
        
        # Show table info
        with get_session() as session:
            product_count = session.query(Product).count()
            category_count = session.query(Category).count()
            
            table = Table(title="Database Status")
            table.add_column("Table", style="cyan")
            table.add_column("Count", style="green")
            
            table.add_row("Products", str(product_count))
            table.add_row("Categories", str(category_count))
            
            console.print(table)
            
    except Exception as e:
        console.print(f"[bold red]✗ Failed to initialize database: {e}[/]")
        raise typer.Exit(1)


@app.command()
def crawl_categories(
    limit_level: int = typer.Option(2, "--limit-level", "-l", help="Maximum category depth"),
    max_categories: int = typer.Option(50, "--max-categories", "-m", help="Maximum categories to crawl"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Crawl categories from the homepage."""
    setup_logging(verbose)
    
    async def _run() -> None:
        runner = CrawlerRunner()
        try:
            console.print("[bold blue]Starting category crawl...[/]")
            await runner.crawl_categories(
                max_depth=limit_level,
                max_categories=max_categories
            )
            console.print("[bold green]✓ Category crawl completed![/]")
        except Exception as e:
            console.print(f"[bold red]✗ Category crawl failed: {e}[/]")
            raise typer.Exit(1)
        finally:
            await runner.close()
    
    asyncio.run(_run())


@app.command()
def crawl_products(
    categories: Optional[str] = typer.Option(None, "--categories", "-c", help="Comma-separated category URLs"),
    max_products: int = typer.Option(200, "--max-products", "-p", help="Maximum products to crawl"),
    concurrency: int = typer.Option(3, "--concurrency", help="Concurrent requests"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Crawl products from specified categories."""
    setup_logging(verbose)
    
    async def _run() -> None:
        runner = CrawlerRunner(concurrency=concurrency)
        try:
            console.print("[bold blue]Starting product crawl...[/]")
            
            category_list = []
            if categories:
                category_list = [cat.strip() for cat in categories.split(",")]
            
            await runner.crawl_products(
                category_urls=category_list,
                max_products=max_products
            )
            console.print("[bold green]✓ Product crawl completed![/]")
        except Exception as e:
            console.print(f"[bold red]✗ Product crawl failed: {e}[/]")
            raise typer.Exit(1)
        finally:
            await runner.close()
    
    asyncio.run(_run())


@app.command()
def crawl_all(
    max_products: int = typer.Option(200, "--max-products", "-p", help="Maximum products to crawl"),
    concurrency: int = typer.Option(3, "--concurrency", help="Concurrent requests"),
    respect_robots: bool = typer.Option(True, "--respect-robots/--no-robots", help="Respect robots.txt"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Run full crawl: categories + products."""
    setup_logging(verbose)
    
    async def _run() -> None:
        runner = CrawlerRunner(
            concurrency=concurrency,
            respect_robots=respect_robots
        )
        try:
            console.print("[bold blue]Starting full crawl...[/]")
            
            # First crawl categories
            console.print("[cyan]Step 1: Crawling categories...[/]")
            await runner.crawl_categories()
            
            # Then crawl products
            console.print("[cyan]Step 2: Crawling products...[/]")
            await runner.crawl_products(max_products=max_products)
            
            console.print("[bold green]✓ Full crawl completed![/]")
            
            # Show summary
            with get_session() as session:
                product_count = session.query(Product).count()
                category_count = session.query(Category).count()
                
                table = Table(title="Crawl Summary")
                table.add_column("Metric", style="cyan")
                table.add_column("Count", style="green")
                
                table.add_row("Categories Found", str(category_count))
                table.add_row("Products Crawled", str(product_count))
                
                console.print(table)
                
        except Exception as e:
            console.print(f"[bold red]✗ Full crawl failed: {e}[/]")
            raise typer.Exit(1)
        finally:
            await runner.close()
    
    asyncio.run(_run())


@app.command()
def resume(
    checkpoint_file: str = typer.Option("checkpoint.json", "--checkpoint", "-c", help="Checkpoint file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Resume crawling from checkpoint."""
    setup_logging(verbose)
    
    checkpoint_path = Path(checkpoint_file)
    if not checkpoint_path.exists():
        console.print(f"[bold red]✗ Checkpoint file not found: {checkpoint_file}[/]")
        raise typer.Exit(1)
    
    async def _run() -> None:
        runner = CrawlerRunner()
        try:
            console.print(f"[bold blue]Resuming crawl from {checkpoint_file}...[/]")
            await runner.resume_from_checkpoint(checkpoint_path)
            console.print("[bold green]✓ Resume completed![/]")
        except Exception as e:
            console.print(f"[bold red]✗ Resume failed: {e}[/]")
            raise typer.Exit(1)
        finally:
            await runner.close()
    
    asyncio.run(_run())


@app.command()
def export(
    format: str = typer.Option("csv", "--format", "-f", help="Export format (csv, json)"),
    output: str = typer.Option("products.csv", "--output", "-o", help="Output file"),
    limit: int = typer.Option(0, "--limit", "-l", help="Limit number of records (0 = all)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Export products to CSV or JSON."""
    setup_logging(verbose)
    
    if format not in ["csv", "json"]:
        console.print("[bold red]✗ Format must be 'csv' or 'json'[/]")
        raise typer.Exit(1)
    
    try:
        console.print(f"[bold blue]Exporting products to {output}...[/]")
        
        exported_count = export_products(
            output_file=output,
            format=format,
            limit=limit if limit > 0 else None
        )
        
        console.print(f"[bold green]✓ Exported {exported_count} products to {output}![/]")
        
    except Exception as e:
        console.print(f"[bold red]✗ Export failed: {e}[/]")
        raise typer.Exit(1)


@app.command()
def status() -> None:
    """Show crawler status and database statistics."""
    try:
        with get_session() as session:
            # Get database statistics
            product_count = session.query(Product).count()
            category_count = session.query(Category).count()
            
            # Create status table
            table = Table(title="DMX Crawler Status")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Total Products", str(product_count))
            table.add_row("Total Categories", str(category_count))
            
            if product_count > 0:
                # Get latest product
                latest_product = session.query(Product).order_by(Product.crawled_at.desc()).first()
                if latest_product:
                    table.add_row("Latest Product", latest_product.name)
                    table.add_row("Last Crawled", str(latest_product.crawled_at))
            
            console.print(table)
            
            # Show recent activity
            if product_count > 0:
                recent_products = (
                    session.query(Product)
                    .order_by(Product.crawled_at.desc())
                    .limit(5)
                    .all()
                )
                
                recent_table = Table(title="Recent Products")
                recent_table.add_column("Name", style="cyan")
                recent_table.add_column("Price", style="green")
                recent_table.add_column("Crawled", style="yellow")
                
                for product in recent_products:
                    price_str = f"{product.price_promo:,} VND" if product.price_promo else "N/A"
                    crawled_str = product.crawled_at.strftime("%Y-%m-%d %H:%M") if product.crawled_at else "N/A"
                    recent_table.add_row(
                        product.name[:50] + "..." if len(product.name) > 50 else product.name,
                        price_str,
                        crawled_str
                    )
                
                console.print(recent_table)
            
    except Exception as e:
        console.print(f"[bold red]✗ Failed to get status: {e}[/]")
        raise typer.Exit(1)


@app.command()
def test_selectors(
    html_file: str = typer.Argument(..., help="HTML file to test selectors on"),
    page_type: str = typer.Option("product", "--type", "-t", help="Page type (home, category, product)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Test selectors against local HTML files."""
    setup_logging(verbose)
    
    html_path = Path(html_file)
    if not html_path.exists():
        console.print(f"[bold red]✗ HTML file not found: {html_file}[/]")
        raise typer.Exit(1)
    
    try:
        from dmx.parsers.test_selectors import test_selectors_on_file
        
        console.print(f"[bold blue]Testing {page_type} selectors on {html_file}...[/]")
        
        results = test_selectors_on_file(html_path, page_type)
        
        # Display results
        table = Table(title=f"Selector Test Results - {page_type.title()}")
        table.add_column("Selector", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Value", style="yellow")
        
        for selector, result in results.items():
            status = "✓ Found" if result["found"] else "✗ Not Found"
            value = str(result["value"])[:50] + "..." if len(str(result["value"])) > 50 else str(result["value"])
            table.add_row(selector, status, value)
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]✗ Selector test failed: {e}[/]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()