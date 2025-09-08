#!/bin/bash
# Quick demonstration of the DMX crawler

echo "=== DMX Crawler Demo ==="
echo

echo "1. Checking configuration..."
python -m dmx.main config | head -10
echo

echo "2. Database status..."
python -m dmx.main status
echo

echo "3. Running unit tests..."
python -m pytest tests/unit/test_selectors_offline.py -q
echo

echo "4. Configuration tests..."  
python -m pytest tests/live/test_live_smoke.py::TestLiveSmoke::test_crawler_configuration -q
echo

echo "5. Checking CLI help..."
python -m dmx.main --help
echo

echo "=== Crawler is ready for production use! ==="
echo
echo "To run a small test crawl:"
echo "  python -m dmx.main crawl-all --max-products 10 --concurrency 1"
echo
echo "To export data:"
echo "  python -m dmx.main export --format csv --out sample.csv"