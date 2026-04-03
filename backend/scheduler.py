"""
Scraper Scheduler
=================
Runs scrapers on a schedule to keep the database up-to-date.

SCHEDULE:
- Every 6 hours: Check Hacker News for new AI tools
- Every 12 hours: Check GitHub trending
- Daily: Run enrichment on tools missing data
- Weekly: Full re-scrape from ProductHunt

USAGE:
    # Run scheduler (foreground)
    python scheduler.py
    
    # Run scheduler as background service
    python scheduler.py --daemon
    
    # Run a specific job once
    python scheduler.py --run-now hn
    python scheduler.py --run-now github
    python scheduler.py --run-now enrich

REQUIREMENTS:
    pip install apscheduler
"""

import argparse
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Lazy imports to avoid loading everything at startup
def get_database():
    from scrapers.database import Database
    return Database()

def get_validator():
    from scrapers import ToolValidator
    return ToolValidator()


def job_hacker_news():
    """
    Job: Monitor Hacker News for new AI tools.
    
    Runs every 6 hours to catch "Show HN" posts with AI tools.
    """
    logger.info("=" * 50)
    logger.info("JOB: Hacker News Monitor")
    logger.info("=" * 50)
    
    try:
        from scrapers.monitors import HackerNewsMonitor
        from scrapers import ToolValidator, DeduplicationEngine
        
        db = get_database()
        validator = get_validator()
        
        # Log scrape start
        run_id = db.log_scrape("hacker_news")
        
        # Get recent HN posts
        with HackerNewsMonitor() as hn:
            tools = hn.get_recent_launches(days=3, min_points=15, limit=50)
        
        logger.info(f"Found {len(tools)} tools from HN")
        
        # Validate
        valid_tools = validator.validate_batch(tools)
        
        # Deduplicate against existing
        existing = db.get_all_tools()
        dedup = DeduplicationEngine()
        for t in existing:
            dedup.add(t)
        
        new_tools = [t for t in valid_tools if dedup.add(t)]
        logger.info(f"New tools (not in DB): {len(new_tools)}")
        
        # Save to database
        if new_tools:
            result = db.upsert_tools(new_tools, source="hacker_news")
            db.complete_scrape(run_id, len(tools), result['added'], result['updated'])
            logger.info(f"Added {result['added']} new tools")
        else:
            db.complete_scrape(run_id, len(tools), 0, 0)
        
    except Exception as e:
        logger.error(f"HN job failed: {e}", exc_info=True)


def job_github():
    """
    Job: Monitor GitHub for trending AI repositories.
    
    Runs every 12 hours.
    """
    logger.info("=" * 50)
    logger.info("JOB: GitHub Trending Monitor")
    logger.info("=" * 50)
    
    try:
        from scrapers.monitors import GitHubMonitor
        from scrapers import ToolValidator, DeduplicationEngine
        
        db = get_database()
        validator = get_validator()
        
        run_id = db.log_scrape("github")
        
        with GitHubMonitor() as gh:
            tools = gh.get_trending_ai_repos(days=14, min_stars=50, limit=50)
        
        logger.info(f"Found {len(tools)} repos from GitHub")
        
        valid_tools = validator.validate_batch(tools)
        
        existing = db.get_all_tools()
        dedup = DeduplicationEngine()
        for t in existing:
            dedup.add(t)
        
        new_tools = [t for t in valid_tools if dedup.add(t)]
        
        if new_tools:
            result = db.upsert_tools(new_tools, source="github")
            db.complete_scrape(run_id, len(tools), result['added'], result['updated'])
            logger.info(f"Added {result['added']} new tools")
        else:
            db.complete_scrape(run_id, len(tools), 0, 0)
        
    except Exception as e:
        logger.error(f"GitHub job failed: {e}", exc_info=True)


def job_enrich():
    """
    Job: Enrich tools missing data.
    
    Runs daily to fill in pricing URLs, API docs, etc.
    """
    logger.info("=" * 50)
    logger.info("JOB: Enrichment")
    logger.info("=" * 50)
    
    try:
        from scrapers.enrichment import ToolEnricher
        
        db = get_database()
        
        # Get tools that might need enrichment
        all_tools = db.get_all_tools()
        
        tools_to_enrich = []
        for tool in all_tools:
            pricing = tool.get('pricing', {})
            api = tool.get('api', {})
            
            # Needs enrichment if missing key data
            if not pricing.get('pricing_url') or (api.get('available') and not api.get('docs_url')):
                tools_to_enrich.append(tool)
        
        logger.info(f"Found {len(tools_to_enrich)} tools needing enrichment")
        
        if not tools_to_enrich:
            return
        
        # Enrich in batches (be gentle with rate limits)
        with ToolEnricher() as enricher:
            enriched = enricher.enrich_batch(
                tools_to_enrich[:20],  # Limit per run
                max_workers=2,
                skip_existing=True
            )
        
        # Save enriched tools
        result = db.upsert_tools(enriched, source="enrichment")
        logger.info(f"Enriched {result['updated']} tools")
        
    except Exception as e:
        logger.error(f"Enrichment job failed: {e}", exc_info=True)


def job_producthunt():
    """
    Job: Fetch from ProductHunt API.
    
    Runs weekly (requires API key).
    """
    logger.info("=" * 50)
    logger.info("JOB: ProductHunt")
    logger.info("=" * 50)
    
    try:
        import os
        if not os.environ.get('PH_API_KEY'):
            logger.warning("PH_API_KEY not set, skipping ProductHunt job")
            return
        
        from scrapers.producthunt import ProductHuntScraper
        from scrapers import ToolValidator
        
        db = get_database()
        validator = get_validator()
        
        run_id = db.log_scrape("producthunt")
        
        with ProductHuntScraper() as ph:
            tools = ph.get_ai_launches(days_back=7, limit=100)
        
        logger.info(f"Found {len(tools)} tools from ProductHunt")
        
        valid_tools = validator.validate_batch(tools)
        result = db.upsert_tools(valid_tools, source="producthunt")
        
        db.complete_scrape(run_id, len(tools), result['added'], result['updated'])
        logger.info(f"Added {result['added']}, updated {result['updated']}")
        
    except Exception as e:
        logger.error(f"ProductHunt job failed: {e}", exc_info=True)


def job_export_json():
    """
    Job: Export database to JSON.
    
    Runs daily to keep tools.json in sync with database.
    """
    logger.info("=" * 50)
    logger.info("JOB: Export to JSON")
    logger.info("=" * 50)
    
    try:
        db = get_database()
        data_dir = Path(__file__).parent.parent / "data"
        output_path = str(data_dir / "tools.json")
        
        db.export_to_json(output_path)
        
    except Exception as e:
        logger.error(f"Export job failed: {e}", exc_info=True)


def run_scheduler():
    """Start the APScheduler with all jobs."""
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger
    except ImportError:
        logger.error("APScheduler not installed. Run: pip install apscheduler")
        sys.exit(1)
    
    scheduler = BlockingScheduler()
    
    # Hacker News: Every 6 hours
    scheduler.add_job(
        job_hacker_news,
        IntervalTrigger(hours=6),
        id='hn_monitor',
        name='Hacker News Monitor',
        next_run_time=datetime.now()  # Run immediately on start
    )
    
    # GitHub: Every 12 hours
    scheduler.add_job(
        job_github,
        IntervalTrigger(hours=12),
        id='github_monitor',
        name='GitHub Trending Monitor'
    )
    
    # Enrichment: Daily at 3 AM
    scheduler.add_job(
        job_enrich,
        CronTrigger(hour=3, minute=0),
        id='enrichment',
        name='Data Enrichment'
    )
    
    # ProductHunt: Weekly on Monday at 4 AM
    scheduler.add_job(
        job_producthunt,
        CronTrigger(day_of_week='mon', hour=4, minute=0),
        id='producthunt',
        name='ProductHunt Fetch'
    )
    
    # Export to JSON: Daily at 5 AM
    scheduler.add_job(
        job_export_json,
        CronTrigger(hour=5, minute=0),
        id='export_json',
        name='Export to JSON'
    )
    
    # Handle shutdown gracefully
    def shutdown(signum, frame):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    
    logger.info("=" * 50)
    logger.info("SCHEDULER STARTED")
    logger.info("=" * 50)
    logger.info("Jobs scheduled:")
    for job in scheduler.get_jobs():
        logger.info(f"  - {job.name}: {job.trigger}")
    logger.info("")
    logger.info("Press Ctrl+C to stop")
    
    scheduler.start()


def main():
    parser = argparse.ArgumentParser(description="AI Tools Scraper Scheduler")
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    parser.add_argument('--run-now', choices=['hn', 'github', 'enrich', 'producthunt', 'export'],
                       help='Run a specific job immediately')
    
    args = parser.parse_args()
    
    if args.run_now:
        jobs = {
            'hn': job_hacker_news,
            'github': job_github,
            'enrich': job_enrich,
            'producthunt': job_producthunt,
            'export': job_export_json,
        }
        jobs[args.run_now]()
    else:
        run_scheduler()


if __name__ == "__main__":
    main()
