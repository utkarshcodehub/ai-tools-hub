"""
Futurepedia Scraper
===================
Scrapes AI tools from Futurepedia.io

HOW FUTUREPEDIA WORKS:
- Main listing at /ai-tools with pagination
- Each tool has a dedicated page /tool/{slug}
- Uses Next.js with client-side rendering (needs special handling)
- Has categories, pricing info, and features

NOTE: This site uses heavy JavaScript. We try HTML first,
but may need Playwright for full scraping.
"""

import re
import json
import logging
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseScraper

logger = logging.getLogger(__name__)


class FuturepediaScraper(BaseScraper):
    """
    Scraper for Futurepedia.io
    
    USAGE:
        with FuturepediaScraper() as scraper:
            tools = scraper.scrape_all(limit=10)  # Get 10 tools for testing
    """
    
    name = "futurepedia"
    base_url = "https://www.futurepedia.io/ai-tools"
    
    # Category mapping from Futurepedia to our schema
    CATEGORY_MAP = {
        "chatbot": "llm",
        "chat": "llm",
        "language model": "llm",
        "llm": "llm",
        "text generation": "llm",
        "coding": "code",
        "code": "code",
        "developer": "code",
        "programming": "code",
        "image generation": "image",
        "image": "image",
        "art": "image",
        "design": "image",
        "video generation": "video",
        "video": "video",
        "video editing": "video",
        "audio": "audio",
        "music": "audio",
        "sound": "audio",
        "voice": "speech",
        "speech": "speech",
        "text to speech": "speech",
        "speech to text": "speech",
        "transcription": "speech",
        "search": "search",
        "research": "search",
        "agent": "agents",
        "automation": "agents",
        "workflow": "agents",
        "embedding": "embeddings",
        "vector": "embeddings",
        "rag": "embeddings",
        "productivity": "productivity",
        "writing": "productivity",
        "note": "productivity",
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tools_found = []
    
    def _map_category(self, category: str) -> Optional[str]:
        """Map Futurepedia category to our schema categories."""
        cat_lower = category.lower().strip()
        
        # Direct match
        if cat_lower in self.CATEGORY_MAP:
            return self.CATEGORY_MAP[cat_lower]
        
        # Partial match
        for key, value in self.CATEGORY_MAP.items():
            if key in cat_lower or cat_lower in key:
                return value
        
        return None
    
    def parse_tool_list(self, html: str) -> list[str]:
        """
        Parse the main listing page for tool URLs.
        
        Futurepedia uses Next.js with __NEXT_DATA__ JSON blob
        containing pre-rendered data - we try to extract that first.
        """
        tool_urls = []
        soup = BeautifulSoup(html, 'lxml')
        
        # Method 1: Try to find Next.js data blob
        next_data = soup.find('script', id='__NEXT_DATA__')
        if next_data:
            try:
                data = json.loads(next_data.string)
                # Navigate the Next.js props structure
                props = data.get('props', {}).get('pageProps', {})
                tools = props.get('tools', []) or props.get('initialTools', [])
                
                for tool in tools:
                    slug = tool.get('slug') or tool.get('id')
                    if slug:
                        url = f"https://www.futurepedia.io/tool/{slug}"
                        tool_urls.append(url)
                        # Also store basic data for later enrichment
                        self.tools_found.append(tool)
                
                if tool_urls:
                    logger.info(f"Found {len(tool_urls)} tools via Next.js data")
                    return tool_urls
            except json.JSONDecodeError:
                logger.warning("Could not parse Next.js data")
        
        # Method 2: Parse HTML links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/tool/' in href:
                url = urljoin(self.base_url, href)
                if url not in tool_urls:
                    tool_urls.append(url)
        
        logger.info(f"Found {len(tool_urls)} tools via HTML parsing")
        return tool_urls
    
    def parse_tool_page(self, html: str, url: str) -> Optional[dict]:
        """
        Parse an individual tool page.
        
        Returns a dict matching our schema.
        """
        soup = BeautifulSoup(html, 'lxml')
        tool = {}
        
        # Try Next.js data first
        next_data = soup.find('script', id='__NEXT_DATA__')
        if next_data:
            try:
                data = json.loads(next_data.string)
                props = data.get('props', {}).get('pageProps', {})
                tool_data = props.get('tool', {})
                
                if tool_data:
                    return self._parse_tool_data(tool_data, url)
            except json.JSONDecodeError:
                pass
        
        # Fallback to HTML parsing
        return self._parse_tool_html(soup, url)
    
    def _parse_tool_data(self, data: dict, url: str) -> dict:
        """Parse tool data from Next.js JSON."""
        # Extract categories
        categories = []
        for cat in data.get('categories', []):
            cat_name = cat.get('name', '') if isinstance(cat, dict) else str(cat)
            mapped = self._map_category(cat_name)
            if mapped and mapped not in categories:
                categories.append(mapped)
        
        # Extract pricing info
        pricing_text = data.get('pricing', '') or ''
        has_free = any(word in pricing_text.lower() for word in ['free', 'freemium', '$0'])
        
        # Build tool dict
        tool = {
            'id': data.get('slug') or data.get('id'),
            'name': data.get('name', ''),
            'tagline': data.get('shortDescription', '') or data.get('description', '')[:80],
            'website': data.get('websiteUrl') or data.get('url') or url,
            'logo_url': data.get('logoUrl') or data.get('logo'),
            'categories': categories,
            'tags': data.get('tags', []) or [],
            'pricing': {
                'has_free_tier': has_free,
                'free_details': pricing_text if has_free else None,
                'paid_starts_at': pricing_text if not has_free else None,
                'pricing_url': data.get('pricingUrl'),
            },
            'api': {
                'available': bool(data.get('hasApi') or data.get('apiUrl')),
                'docs_url': data.get('apiUrl') or data.get('docsUrl'),
            },
            'status': 'active',
        }
        
        return tool
    
    def _parse_tool_html(self, soup: BeautifulSoup, url: str) -> Optional[dict]:
        """Fallback HTML parsing when Next.js data isn't available."""
        # Find tool name (usually in h1)
        name_el = soup.find('h1')
        if not name_el:
            logger.warning(f"Could not find tool name in {url}")
            return None
        
        name = name_el.get_text(strip=True)
        
        # Find description
        desc_el = soup.find('meta', {'name': 'description'})
        description = desc_el.get('content', '') if desc_el else ''
        
        # Find website link (usually labeled "Visit Website" or similar)
        website = url  # Default to Futurepedia page
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True).lower()
            if any(word in text for word in ['visit', 'website', 'official']):
                website = link['href']
                break
        
        return {
            'name': name,
            'tagline': description[:80] if description else f"{name} - AI tool",
            'website': website,
            'categories': [],
            'tags': [],
            'pricing': {'has_free_tier': False},
            'api': {'available': False},
            'status': 'active',
        }
    
    def scrape_categories(self) -> list[dict]:
        """
        Scrape tools organized by category.
        
        Futurepedia has category pages like /ai-tools/chatbots
        """
        all_tools = []
        category_slugs = [
            'chatbots', 'code-assistants', 'image-generators',
            'video', 'audio', 'writing', 'productivity',
            'search-engines', 'agents'
        ]
        
        for cat_slug in category_slugs:
            url = f"https://www.futurepedia.io/ai-tools/{cat_slug}"
            logger.info(f"Scraping category: {cat_slug}")
            
            html = self.fetch(url)
            if html:
                urls = self.parse_tool_list(html)
                for tool_url in urls[:50]:  # Limit per category
                    tool_html = self.fetch(tool_url)
                    if tool_html:
                        tool = self.parse_tool_page(tool_html, tool_url)
                        if tool:
                            all_tools.append(tool)
        
        return all_tools
