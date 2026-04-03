"""
Deduplication Engine
====================
Detects and merges duplicate tools from different scrapers.

WHY THIS MATTERS:
- "ChatGPT", "GPT-4", "OpenAI GPT" might all refer to the same tool
- Different sources have different names for the same thing
- We want ONE entry per tool, not five slightly different ones

HOW IT WORKS:
1. Domain matching - same website = same tool
2. Name similarity - fuzzy string matching
3. Merge strategy - combine data from multiple sources
"""

import logging
from typing import Optional
from urllib.parse import urlparse
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


def normalize_domain(url: str) -> str:
    """
    Extract and normalize domain from URL.
    
    Examples:
        "https://www.openai.com/chatgpt" -> "openai.com"
        "https://chat.openai.com" -> "openai.com"  (removes subdomain)
        "http://claude.ai/" -> "claude.ai"
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Remove www prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Remove common subdomains (but keep meaningful ones like "chat")
        # This is tricky - "chat.openai.com" and "openai.com" are same company
        # but "vercel.app" subdomains are different projects
        parts = domain.split('.')
        
        # If it's a known platform domain, keep subdomain
        platform_domains = {'vercel.app', 'netlify.app', 'github.io', 'herokuapp.com'}
        if len(parts) >= 3 and '.'.join(parts[-2:]) in platform_domains:
            return domain  # Keep full domain for platforms
        
        # Otherwise, use main domain (last 2 parts for .com, .ai, etc.)
        if len(parts) >= 2:
            # Handle .co.uk style domains
            if parts[-2] in ('co', 'com', 'org', 'net'):
                return '.'.join(parts[-3:]) if len(parts) >= 3 else domain
            return '.'.join(parts[-2:])
        
        return domain
    except Exception:
        return url.lower()


def normalize_name(name: str) -> str:
    """
    Normalize tool name for comparison.
    
    Examples:
        "GPT-4o" -> "gpt4o"
        "DALL·E 3" -> "dalle3"
        "Claude 3.5 Sonnet" -> "claude35sonnet"
    """
    # Lowercase
    name = name.lower()
    # Remove special chars, spaces, hyphens
    name = ''.join(c for c in name if c.isalnum())
    return name


def name_similarity(name1: str, name2: str) -> float:
    """
    Calculate similarity ratio between two names (0.0 to 1.0).
    
    Uses Python's built-in SequenceMatcher which implements
    a ratio based on longest contiguous matching subsequence.
    
    Examples:
        "ChatGPT" vs "Chat GPT" -> ~0.9 (very similar)
        "GPT-4" vs "GPT-4o" -> ~0.8 (similar)
        "Claude" vs "Gemini" -> ~0.3 (different)
    """
    # Normalize both names
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)
    
    # SequenceMatcher compares sequences
    return SequenceMatcher(None, n1, n2).ratio()


class DeduplicationEngine:
    """
    Detects and handles duplicate tools.
    
    USAGE:
        dedup = DeduplicationEngine()
        
        # Add tools one by one
        for tool in scraped_tools:
            dedup.add(tool)
        
        # Get deduplicated list
        unique_tools = dedup.get_unique()
    
    MATCHING RULES (in order of confidence):
    1. Same domain -> definitely same tool (merge)
    2. Name similarity > 0.85 AND same category -> probably same (merge)
    3. Name similarity > 0.7 -> flag for manual review
    """
    
    def __init__(self, domain_threshold: float = 1.0, name_threshold: float = 0.85):
        """
        Args:
            domain_threshold: Similarity needed for domain match (1.0 = exact)
            name_threshold: Similarity needed for name match (0.85 = high confidence)
        """
        self.tools: list[dict] = []
        self.domain_index: dict[str, int] = {}  # domain -> tool index
        self.name_threshold = name_threshold
        self.duplicates_found = 0
        self.merges_performed = 0
    
    def add(self, tool: dict) -> bool:
        """
        Add a tool, checking for duplicates.
        
        Returns True if this was a new tool, False if it was merged with existing.
        """
        # Check domain first (most reliable)
        domain = normalize_domain(tool.get('website', ''))
        
        if domain and domain in self.domain_index:
            existing_idx = self.domain_index[domain]
            self._merge(existing_idx, tool)
            self.duplicates_found += 1
            logger.debug(f"Domain match: '{tool['name']}' merged with '{self.tools[existing_idx]['name']}'")
            return False
        
        # Check name similarity (less reliable but catches more)
        for idx, existing in enumerate(self.tools):
            similarity = name_similarity(tool.get('name', ''), existing.get('name', ''))
            
            if similarity >= self.name_threshold:
                # Also check if they share a category (extra confidence)
                tool_cats = set(tool.get('categories', []))
                existing_cats = set(existing.get('categories', []))
                
                if tool_cats & existing_cats:  # If any category overlaps
                    self._merge(idx, tool)
                    self.duplicates_found += 1
                    logger.debug(f"Name match ({similarity:.2f}): '{tool['name']}' merged with '{existing['name']}'")
                    return False
        
        # No match found - add as new tool
        idx = len(self.tools)
        self.tools.append(tool)
        if domain:
            self.domain_index[domain] = idx
        
        return True
    
    def _merge(self, existing_idx: int, new_tool: dict) -> None:
        """
        Merge new tool data into existing tool.
        
        MERGE STRATEGY:
        - For strings: keep existing if non-empty, else use new
        - For lists: combine and deduplicate
        - For booleans: OR them (if either says True, it's True)
        - For nested dicts: merge recursively
        """
        existing = self.tools[existing_idx]
        
        # Merge top-level string fields (prefer existing)
        for field in ['name', 'tagline', 'website', 'logo_url', 'status']:
            if not existing.get(field) and new_tool.get(field):
                existing[field] = new_tool[field]
        
        # Merge lists (combine unique values)
        for field in ['categories', 'tags', 'free_alternatives']:
            existing_list = existing.get(field, [])
            new_list = new_tool.get(field, [])
            # Combine and deduplicate while preserving order
            combined = list(dict.fromkeys(existing_list + new_list))
            existing[field] = combined
        
        # Merge pricing (prefer filled values)
        if 'pricing' in new_tool:
            if 'pricing' not in existing:
                existing['pricing'] = {}
            for key, value in new_tool['pricing'].items():
                if value and not existing['pricing'].get(key):
                    existing['pricing'][key] = value
            # has_free_tier is True if either source says so
            if new_tool['pricing'].get('has_free_tier'):
                existing['pricing']['has_free_tier'] = True
        
        # Merge API info (prefer filled values)
        if 'api' in new_tool:
            if 'api' not in existing:
                existing['api'] = {}
            for key, value in new_tool['api'].items():
                if value and not existing['api'].get(key):
                    existing['api'][key] = value
            # available is True if either source says so
            if new_tool['api'].get('available'):
                existing['api']['available'] = True
        
        self.merges_performed += 1
    
    def get_unique(self) -> list[dict]:
        """Get list of unique tools after deduplication."""
        return self.tools.copy()
    
    def find_potential_duplicates(self, threshold: float = 0.7) -> list[tuple[dict, dict, float]]:
        """
        Find tools that MIGHT be duplicates but weren't auto-merged.
        
        Returns list of (tool1, tool2, similarity) tuples for manual review.
        
        Useful for finding things like:
        - "ChatGPT" vs "OpenAI GPT-4" (same company, different product names)
        """
        potential = []
        
        for i, tool1 in enumerate(self.tools):
            for j, tool2 in enumerate(self.tools[i+1:], i+1):
                similarity = name_similarity(tool1.get('name', ''), tool2.get('name', ''))
                
                if threshold <= similarity < self.name_threshold:
                    potential.append((tool1, tool2, similarity))
        
        return potential
    
    def get_stats(self) -> dict:
        """Get deduplication statistics."""
        return {
            'total_processed': len(self.tools) + self.duplicates_found,
            'unique_tools': len(self.tools),
            'duplicates_found': self.duplicates_found,
            'merges_performed': self.merges_performed,
        }


def deduplicate_tools(tools: list[dict], **kwargs) -> list[dict]:
    """
    Convenience function to deduplicate a list of tools.
    
    Usage:
        unique_tools = deduplicate_tools(all_scraped_tools)
    """
    engine = DeduplicationEngine(**kwargs)
    
    for tool in tools:
        engine.add(tool)
    
    stats = engine.get_stats()
    logger.info(f"Deduplication: {stats['total_processed']} -> {stats['unique_tools']} tools "
                f"({stats['duplicates_found']} duplicates found)")
    
    return engine.get_unique()
