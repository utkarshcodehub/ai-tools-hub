"""
Scraper Runner
==============
Main entry point for running all scrapers and updating tools.json

USAGE:
    # Test with small sample
    python run_scrapers.py --test
    
    # Run specific scraper
    python run_scrapers.py --source futurepedia --limit 100
    
    # Run all scrapers and update tools.json
    python run_scrapers.py --all
"""

import argparse
import json
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Import our modules
from scrapers import ToolValidator, DeduplicationEngine
from scrapers.futurepedia import FuturepediaScraper
from scrapers.taaft import TAFTScraper
from scrapers.producthunt import ProductHuntScraper


def load_existing_tools(path: Path) -> list[dict]:
    """Load existing tools from tools.json"""
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_tools(tools: list[dict], path: Path) -> None:
    """Save tools to JSON file with pretty formatting."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(tools, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(tools)} tools to {path}")


def run_futurepedia(limit: int = None) -> list[dict]:
    """Run Futurepedia scraper."""
    logger.info("=" * 50)
    logger.info("Running Futurepedia scraper")
    logger.info("=" * 50)
    
    with FuturepediaScraper(requests_per_second=0.5) as scraper:
        tools = scraper.scrape_all(limit=limit)
    
    logger.info(f"Futurepedia: scraped {len(tools)} tools")
    return tools


def run_taaft(limit: int = None, use_playwright: bool = False) -> list[dict]:
    """Run There's An AI For That scraper."""
    logger.info("=" * 50)
    logger.info("Running TAAFT scraper")
    logger.info("=" * 50)
    
    with TAFTScraper(use_playwright=use_playwright, requests_per_second=0.5) as scraper:
        # Try sitemap first (less likely to be blocked)
        tools = scraper.scrape_from_sitemap(limit=limit)
        
        if not tools and use_playwright:
            # Fall back to full scraping with Playwright
            tools = scraper.scrape_all(limit=limit)
    
    logger.info(f"TAAFT: scraped {len(tools)} tools")
    return tools


def run_producthunt(limit: int = 50, days_back: int = 30) -> list[dict]:
    """Run ProductHunt scraper."""
    logger.info("=" * 50)
    logger.info("Running ProductHunt scraper")
    logger.info("=" * 50)
    
    with ProductHuntScraper() as scraper:
        tools = scraper.get_ai_launches(days_back=days_back, limit=limit)
    
    logger.info(f"ProductHunt: fetched {len(tools)} tools")
    return tools


def merge_and_deduplicate(
    new_tools: list[dict],
    existing_tools: list[dict],
    validator: ToolValidator
) -> list[dict]:
    """
    Merge new tools with existing, validate, and deduplicate.
    
    STRATEGY:
    1. Validate all new tools
    2. Add existing tools to dedup engine (they're the "source of truth")
    3. Add new tools (duplicates will be merged)
    4. Return combined list
    """
    logger.info("=" * 50)
    logger.info("Merging and deduplicating")
    logger.info("=" * 50)
    
    # Validate new tools
    valid_new = validator.validate_batch(new_tools)
    logger.info(f"Validated {len(valid_new)}/{len(new_tools)} new tools")
    
    # Setup deduplication
    dedup = DeduplicationEngine()
    
    # Add existing tools first (they have priority)
    for tool in existing_tools:
        dedup.add(tool)
    
    # Add new tools (will merge with existing if duplicate)
    new_count = 0
    for tool in valid_new:
        if dedup.add(tool):
            new_count += 1
    
    logger.info(f"Added {new_count} new unique tools")
    
    # Get stats
    stats = dedup.get_stats()
    logger.info(f"Deduplication stats: {stats}")
    
    # Find potential duplicates for manual review
    potential_dupes = dedup.find_potential_duplicates(threshold=0.7)
    if potential_dupes:
        logger.warning(f"Found {len(potential_dupes)} potential duplicates for manual review:")
        for tool1, tool2, similarity in potential_dupes[:5]:  # Show first 5
            logger.warning(f"  {tool1['name']} <-> {tool2['name']} ({similarity:.0%})")
    
    return dedup.get_unique()


def main():
    parser = argparse.ArgumentParser(description="Run AI tool scrapers")
    parser.add_argument('--test', action='store_true', help='Test mode (small sample)')
    parser.add_argument('--all', action='store_true', help='Run all scrapers')
    parser.add_argument('--source', choices=['futurepedia', 'taaft', 'producthunt'],
                       help='Run specific scraper')
    parser.add_argument('--limit', type=int, default=None, help='Limit tools per source')
    parser.add_argument('--playwright', action='store_true', help='Use Playwright for TAAFT')
    parser.add_argument('--dry-run', action='store_true', help="Don't save results")
    parser.add_argument('--output', type=str, help='Output file path')
    
    args = parser.parse_args()
    
    # Paths
    base_dir = Path(__file__).parent
    data_dir = base_dir.parent / "data"
    tools_path = Path(args.output) if args.output else data_dir / "tools.json"
    
    # Load existing tools
    existing_tools = load_existing_tools(tools_path)
    logger.info(f"Loaded {len(existing_tools)} existing tools")
    
    # Validator
    validator = ToolValidator()
    
    # Collect new tools
    all_new_tools = []
    
    # Test mode: small sample
    if args.test:
        args.limit = args.limit or 5
        logger.info(f"TEST MODE: limiting to {args.limit} tools per source")
    
    # Run scrapers
    if args.all or args.source == 'futurepedia':
        all_new_tools.extend(run_futurepedia(limit=args.limit))
    
    if args.all or args.source == 'taaft':
        all_new_tools.extend(run_taaft(limit=args.limit, use_playwright=args.playwright))
    
    if args.all or args.source == 'producthunt':
        all_new_tools.extend(run_producthunt(limit=args.limit or 50))
    
    # If no source specified and not --all, show help
    if not all_new_tools and not args.all and not args.source:
        parser.print_help()
        return
    
    # Merge with existing
    final_tools = merge_and_deduplicate(all_new_tools, existing_tools, validator)
    
    # Sort by name
    final_tools.sort(key=lambda x: x.get('name', '').lower())
    
    # Summary
    logger.info("=" * 50)
    logger.info("SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Existing tools: {len(existing_tools)}")
    logger.info(f"New tools scraped: {len(all_new_tools)}")
    logger.info(f"Final unique tools: {len(final_tools)}")
    logger.info(f"Net new: {len(final_tools) - len(existing_tools)}")
    
    # Save results
    if not args.dry_run:
        save_tools(final_tools, tools_path)
        
        # Also save a backup with timestamp
        backup_path = data_dir / f"tools_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        save_tools(existing_tools, backup_path)
        logger.info(f"Backup saved to {backup_path}")
    else:
        logger.info("DRY RUN: results not saved")


if __name__ == "__main__":
    main()
