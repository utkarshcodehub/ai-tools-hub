"""
Enrichment Runner
=================
Enriches existing tools.json with pricing, API docs, and better descriptions.

USAGE:
    # Enrich all tools (skip already enriched)
    python run_enrichment.py
    
    # Force re-enrich everything
    python run_enrichment.py --force
    
    # Only enrich specific tools
    python run_enrichment.py --tools openai-gpt4o,anthropic-claude
    
    # Test mode (first 5 tools)
    python run_enrichment.py --test
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

from scrapers.enrichment import ToolEnricher, LLMEnricher


def load_tools(path: Path) -> list[dict]:
    """Load tools from JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_tools(tools: list[dict], path: Path) -> None:
    """Save tools to JSON file."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(tools, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(tools)} tools to {path}")


def needs_enrichment(tool: dict) -> bool:
    """Check if a tool needs enrichment."""
    # Missing pricing URL
    pricing = tool.get('pricing', {})
    if not pricing.get('pricing_url'):
        return True
    
    # Missing API docs
    api = tool.get('api', {})
    if api.get('available') and not api.get('docs_url'):
        return True
    
    # Missing logo
    if not tool.get('logo_url'):
        return True
    
    return False


def main():
    parser = argparse.ArgumentParser(description="Enrich AI tools data")
    parser.add_argument('--test', action='store_true', help='Test mode (5 tools)')
    parser.add_argument('--force', action='store_true', help='Re-enrich all tools')
    parser.add_argument('--tools', type=str, help='Comma-separated tool IDs')
    parser.add_argument('--workers', type=int, default=3, help='Parallel workers')
    parser.add_argument('--use-llm', action='store_true', help='Use LLM for taglines')
    parser.add_argument('--dry-run', action='store_true', help="Don't save results")
    parser.add_argument('--input', type=str, help='Input JSON file')
    parser.add_argument('--output', type=str, help='Output JSON file')
    
    args = parser.parse_args()
    
    # Paths
    base_dir = Path(__file__).parent
    data_dir = base_dir.parent / "data"
    input_path = Path(args.input) if args.input else data_dir / "tools.json"
    output_path = Path(args.output) if args.output else input_path
    
    # Load tools
    all_tools = load_tools(input_path)
    logger.info(f"Loaded {len(all_tools)} tools")
    
    # Filter tools to enrich
    if args.tools:
        tool_ids = set(args.tools.split(','))
        tools_to_enrich = [t for t in all_tools if t.get('id') in tool_ids]
    elif args.force:
        tools_to_enrich = all_tools
    else:
        tools_to_enrich = [t for t in all_tools if needs_enrichment(t)]
    
    if args.test:
        tools_to_enrich = tools_to_enrich[:5]
    
    logger.info(f"Will enrich {len(tools_to_enrich)} tools")
    
    if not tools_to_enrich:
        logger.info("No tools need enrichment")
        return
    
    # Build index for updating
    tool_index = {t['id']: i for i, t in enumerate(all_tools)}
    
    # Enrich tools
    with ToolEnricher() as enricher:
        logger.info("=" * 50)
        logger.info("Running web enrichment (pricing, API docs)")
        logger.info("=" * 50)
        
        enriched = enricher.enrich_batch(
            tools_to_enrich, 
            max_workers=args.workers,
            skip_existing=not args.force
        )
        
        # Update original list
        for tool in enriched:
            idx = tool_index.get(tool['id'])
            if idx is not None:
                all_tools[idx] = tool
    
    # LLM enrichment (optional)
    if args.use_llm:
        logger.info("=" * 50)
        logger.info("Running LLM enrichment (taglines)")
        logger.info("=" * 50)
        
        with LLMEnricher() as llm:
            for tool in enriched:
                if not tool.get('tagline') or len(tool['tagline']) < 20:
                    new_tagline = llm.generate_tagline(
                        tool['name'],
                        tool['website'],
                        tool.get('tagline', '')
                    )
                    if new_tagline:
                        tool['tagline'] = new_tagline
                        logger.info(f"  {tool['name']}: {new_tagline}")
                
                # Update categories if empty
                if not tool.get('categories'):
                    categories = llm.categorize_tool(
                        tool['name'],
                        tool.get('tagline', ''),
                        tool['website']
                    )
                    if categories:
                        tool['categories'] = categories
                        logger.info(f"  {tool['name']}: categories = {categories}")
                
                # Update in main list
                idx = tool_index.get(tool['id'])
                if idx is not None:
                    all_tools[idx] = tool
    
    # Summary
    logger.info("=" * 50)
    logger.info("ENRICHMENT SUMMARY")
    logger.info("=" * 50)
    
    pricing_found = sum(1 for t in all_tools if t.get('pricing', {}).get('pricing_url'))
    api_found = sum(1 for t in all_tools if t.get('api', {}).get('docs_url'))
    free_tier = sum(1 for t in all_tools if t.get('pricing', {}).get('has_free_tier'))
    
    logger.info(f"Tools with pricing URL: {pricing_found}/{len(all_tools)}")
    logger.info(f"Tools with API docs: {api_found}/{len(all_tools)}")
    logger.info(f"Tools with free tier: {free_tier}/{len(all_tools)}")
    
    # Save
    if not args.dry_run:
        # Backup first
        backup_path = data_dir / f"tools_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        save_tools(load_tools(input_path), backup_path)
        
        # Save enriched
        save_tools(all_tools, output_path)
    else:
        logger.info("DRY RUN: results not saved")


if __name__ == "__main__":
    main()
