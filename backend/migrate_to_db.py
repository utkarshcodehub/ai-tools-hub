"""
Database Migration Script
=========================
Imports existing tools.json into the SQLite database.

USAGE:
    # Import tools.json to database
    python migrate_to_db.py
    
    # Export database back to JSON
    python migrate_to_db.py --export
    
    # Show database stats
    python migrate_to_db.py --stats
"""

import argparse
import json
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

from scrapers.database import Database


def main():
    parser = argparse.ArgumentParser(description="Database migration tool")
    parser.add_argument('--import-json', type=str, help='Import from JSON file')
    parser.add_argument('--export', action='store_true', help='Export DB to JSON')
    parser.add_argument('--stats', action='store_true', help='Show database stats')
    parser.add_argument('--db', type=str, help='Database path')
    
    args = parser.parse_args()
    
    # Initialize database
    db = Database(args.db)
    
    # Default action: import existing tools.json
    if not args.export and not args.stats:
        data_dir = Path(__file__).parent.parent / "data"
        json_path = args.import_json or str(data_dir / "tools.json")
        
        if not Path(json_path).exists():
            logger.error(f"File not found: {json_path}")
            return
        
        logger.info(f"Importing from {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            tools = json.load(f)
        
        logger.info(f"Found {len(tools)} tools in JSON")
        
        result = db.upsert_tools(tools, source="json_import")
        
        logger.info("=" * 50)
        logger.info("IMPORT COMPLETE")
        logger.info("=" * 50)
        logger.info(f"Added: {result['added']}")
        logger.info(f"Updated: {result['updated']}")
    
    # Export to JSON
    if args.export:
        data_dir = Path(__file__).parent.parent / "data"
        output_path = str(data_dir / "tools_from_db.json")
        
        db.export_to_json(output_path)
        logger.info(f"Exported to {output_path}")
    
    # Show stats
    if args.stats or not args.export:
        stats = db.get_stats()
        
        logger.info("=" * 50)
        logger.info("DATABASE STATISTICS")
        logger.info("=" * 50)
        logger.info(f"Total tools: {stats['total_tools']}")
        logger.info(f"With free tier: {stats['with_free_tier']}")
        logger.info(f"With API: {stats['with_api']}")
        logger.info("")
        logger.info("By category:")
        for cat_id, info in stats['by_category'].items():
            logger.info(f"  {info['label']}: {info['count']}")


if __name__ == "__main__":
    main()
