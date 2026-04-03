"""
Monitor Runner
==============
Discover new AI tools from Hacker News and GitHub.

USAGE:
    # Discover tools from last 7 days
    python run_monitors.py
    
    # Discover tools from last 30 days
    python run_monitors.py --days 30
    
    # Only check Hacker News
    python run_monitors.py --source hn
    
    # Add discovered tools to tools.json
    python run_monitors.py --save
"""

import argparse
import json
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

from scrapers.monitors import HackerNewsMonitor, GitHubMonitor
from scrapers import ToolValidator, DeduplicationEngine


def load_tools(path: Path) -> list[dict]:
    """Load existing tools."""
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_tools(tools: list[dict], path: Path) -> None:
    """Save tools to JSON."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(tools, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(tools)} tools to {path}")


def main():
    parser = argparse.ArgumentParser(description="Discover new AI tools")
    parser.add_argument('--days', type=int, default=7, help='Days to look back')
    parser.add_argument('--source', choices=['hn', 'github', 'all'], default='all')
    parser.add_argument('--min-points', type=int, default=20, help='Min HN points')
    parser.add_argument('--min-stars', type=int, default=100, help='Min GitHub stars')
    parser.add_argument('--save', action='store_true', help='Save to tools.json')
    parser.add_argument('--dry-run', action='store_true', help='Show but dont save')
    
    args = parser.parse_args()
    
    discovered = []
    
    # Hacker News
    if args.source in ('hn', 'all'):
        logger.info("=" * 50)
        logger.info("Checking Hacker News...")
        logger.info("=" * 50)
        
        with HackerNewsMonitor() as hn:
            hn_tools = hn.get_recent_launches(
                days=args.days,
                min_points=args.min_points,
                limit=30
            )
            discovered.extend(hn_tools)
            
            for tool in hn_tools[:10]:
                logger.info(f"  📰 {tool['name']}: {tool['tagline'][:50]}...")
    
    # GitHub
    if args.source in ('github', 'all'):
        logger.info("=" * 50)
        logger.info("Checking GitHub trending...")
        logger.info("=" * 50)
        
        with GitHubMonitor() as gh:
            gh_tools = gh.get_trending_ai_repos(
                days=args.days * 4,  # GitHub repos take longer to get stars
                min_stars=args.min_stars,
                limit=30
            )
            discovered.extend(gh_tools)
            
            for tool in gh_tools[:10]:
                logger.info(f"  ⭐ {tool['name']}: {tool['tagline'][:50]}...")
    
    # Validate and deduplicate
    logger.info("=" * 50)
    logger.info("Processing discovered tools...")
    logger.info("=" * 50)
    
    validator = ToolValidator()
    valid_tools = validator.validate_batch(discovered)
    
    # Deduplicate against existing tools
    base_dir = Path(__file__).parent
    data_dir = base_dir.parent / "data"
    tools_path = data_dir / "tools.json"
    
    existing_tools = load_tools(tools_path)
    
    dedup = DeduplicationEngine()
    for tool in existing_tools:
        dedup.add(tool)
    
    new_tools = []
    for tool in valid_tools:
        if dedup.add(tool):  # Returns True if tool is new
            new_tools.append(tool)
    
    # Summary
    logger.info("=" * 50)
    logger.info("DISCOVERY SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Discovered: {len(discovered)} tools")
    logger.info(f"Valid: {len(valid_tools)} tools")
    logger.info(f"New (not in existing): {len(new_tools)} tools")
    
    if new_tools:
        logger.info("\n🆕 New tools discovered:")
        for tool in new_tools:
            logger.info(f"  • {tool['name']} - {tool['website']}")
    
    # Save if requested
    if args.save and new_tools and not args.dry_run:
        all_tools = dedup.get_unique()
        all_tools.sort(key=lambda x: x.get('name', '').lower())
        
        # Backup
        backup_path = data_dir / f"tools_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        save_tools(existing_tools, backup_path)
        
        # Save updated
        save_tools(all_tools, tools_path)
        logger.info(f"Added {len(new_tools)} new tools!")
    elif args.dry_run:
        logger.info("DRY RUN: not saved")


if __name__ == "__main__":
    main()
