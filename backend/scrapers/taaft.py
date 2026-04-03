"""
There's An AI For That (TAAFT) Scraper
======================================
Scrapes AI tools from theresanaiforthat.com

HOW TAAFT WORKS:
- Homepage shows "Just Released" tools
- Category pages at /s/{category}/
- Individual tool pages at /{tool-slug}/
- Heavy anti-bot protection (403s) - needs browser simulation

STRATEGY:
Since TAAFT blocks simple HTTP requests, we provide two modes:
1. playwright_mode=True: Uses real browser (slower but works)
2. playwright_mode=False: Uses sitemap/RSS if available
"""

import re
import json
import logging
import xml.etree.ElementTree as ET
from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .base import BaseScraper

logger = logging.getLogger(__name__)


class TAFTScraper(BaseScraper):
    """
    Scraper for There's An AI For That (theresanaiforthat.com)
    
    NOTE: This site has strong anti-bot protection.
    For production use, you'll need to use Playwright mode.
    
    USAGE:
        # Basic mode (may get blocked)
        with TAFTScraper() as scraper:
            tools = scraper.scrape_from_sitemap(limit=100)
        
        # With Playwright (requires: pip install playwright && playwright install)
        with TAFTScraper(use_playwright=True) as scraper:
            tools = scraper.scrape_all(limit=100)
    """
    
    name = "taaft"
    base_url = "https://theresanaiforthat.com/"
    sitemap_url = "https://theresanaiforthat.com/sitemap.xml"
    
    # TAAFT uses different category names
    CATEGORY_MAP = {
        "chatbots": "llm",
        "chat": "llm",
        "large-language-models": "llm",
        "llm": "llm",
        "text-generators": "llm",
        "copywriting": "productivity",
        "code-assistant": "code",
        "coding": "code",
        "developer-tools": "code",
        "programming": "code",
        "image-generator": "image",
        "image-generators": "image",
        "art": "image",
        "design": "image",
        "avatars": "image",
        "video-generator": "video",
        "video-generators": "video",
        "video-editing": "video",
        "music": "audio",
        "audio": "audio",
        "voice": "speech",
        "speech-to-text": "speech",
        "text-to-speech": "speech",
        "transcription": "speech",
        "search-engine": "search",
        "research": "search",
        "agents": "agents",
        "automation": "agents",
        "productivity": "productivity",
        "writing": "productivity",
        "note-taking": "productivity",
        "email": "productivity",
    }
    
    def __init__(self, use_playwright: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.use_playwright = use_playwright
        self._playwright = None
        self._browser = None
    
    def _map_category(self, category: str) -> Optional[str]:
        """Map TAAFT category to our schema."""
        cat_lower = category.lower().strip().replace(' ', '-')
        
        if cat_lower in self.CATEGORY_MAP:
            return self.CATEGORY_MAP[cat_lower]
        
        for key, value in self.CATEGORY_MAP.items():
            if key in cat_lower:
                return value
        
        return None
    
    def _init_playwright(self):
        """Initialize Playwright browser if needed."""
        if self._browser is not None:
            return
        
        try:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
            logger.info("Playwright browser initialized")
        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
            raise
    
    def _fetch_with_playwright(self, url: str) -> Optional[str]:
        """Fetch URL using Playwright browser."""
        self._init_playwright()
        
        try:
            page = self._browser.new_page()
            page.goto(url, wait_until='networkidle', timeout=30000)
            content = page.content()
            page.close()
            return content
        except Exception as e:
            logger.error(f"Playwright fetch failed for {url}: {e}")
            return None
    
    def fetch(self, url: str, use_cache: bool = True) -> Optional[str]:
        """Override fetch to optionally use Playwright."""
        if self.use_playwright:
            # Check cache first
            if use_cache:
                cached = self.cache.get(url)
                if cached:
                    return cached
            
            self.rate_limiter.wait_if_needed(url)
            content = self._fetch_with_playwright(url)
            
            if content and use_cache:
                self.cache.set(url, content)
            
            return content
        
        return super().fetch(url, use_cache)
    
    def parse_tool_list(self, html: str) -> list[str]:
        """Parse homepage or category page for tool URLs."""
        tool_urls = []
        soup = BeautifulSoup(html, 'lxml')
        
        # Look for tool links (usually to /{slug}/ format)
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # TAAFT tool pages are at root level like /chatgpt/
            # Exclude known non-tool paths
            exclude_patterns = [
                '/s/', '/search', '/about', '/contact', '/privacy',
                '/terms', '/login', '/signup', '/api', '/sitemap',
                '/just-released', '/trending', '/categories'
            ]
            
            if href.startswith('/') and not any(p in href for p in exclude_patterns):
                # Check it looks like a tool slug (not too long, has chars)
                slug = href.strip('/')
                if slug and len(slug) < 100 and re.match(r'^[a-z0-9-]+$', slug, re.I):
                    url = urljoin(self.base_url, href)
                    if url not in tool_urls:
                        tool_urls.append(url)
        
        logger.info(f"Found {len(tool_urls)} potential tool URLs")
        return tool_urls
    
    def parse_tool_page(self, html: str, url: str) -> Optional[dict]:
        """Parse an individual tool page."""
        soup = BeautifulSoup(html, 'lxml')
        
        # Extract tool name from h1 or title
        name = None
        h1 = soup.find('h1')
        if h1:
            name = h1.get_text(strip=True)
        
        if not name:
            title = soup.find('title')
            if title:
                # Usually "ToolName - There's An AI For That"
                name = title.get_text(strip=True).split(' - ')[0].split(' | ')[0]
        
        if not name:
            logger.warning(f"Could not find tool name in {url}")
            return None
        
        # Extract description
        description = ""
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc:
            description = meta_desc.get('content', '')
        
        # Find website link
        website = None
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True).lower()
            
            # Look for external link that's the tool's website
            if href.startswith('http') and 'theresanaiforthat.com' not in href:
                if any(word in text for word in ['visit', 'website', 'open', 'try', 'go to']):
                    website = href
                    break
        
        if not website:
            # Try to find any external link
            for link in soup.find_all('a', href=True, rel=lambda x: x and 'nofollow' in x):
                href = link['href']
                if href.startswith('http') and 'theresanaiforthat.com' not in href:
                    website = href
                    break
        
        # Extract categories from breadcrumbs or tags
        categories = []
        for el in soup.find_all(['a', 'span'], class_=lambda x: x and 'category' in str(x).lower()):
            cat_text = el.get_text(strip=True)
            mapped = self._map_category(cat_text)
            if mapped and mapped not in categories:
                categories.append(mapped)
        
        # Check for pricing info
        pricing_text = ""
        has_free = False
        for el in soup.find_all(text=re.compile(r'(free|pricing|\$|paid|subscription)', re.I)):
            pricing_text = str(el)[:100]
            if 'free' in pricing_text.lower():
                has_free = True
                break
        
        return {
            'name': name,
            'tagline': description[:80] if description else f"{name} - AI tool",
            'website': website or url,
            'categories': categories,
            'tags': [],
            'pricing': {
                'has_free_tier': has_free,
                'free_details': pricing_text if has_free else None,
            },
            'api': {'available': False},
            'status': 'active',
        }
    
    def scrape_from_sitemap(self, limit: Optional[int] = None) -> list[dict]:
        """
        Alternative scraping method using sitemap.xml
        
        Sitemaps are usually not blocked and contain all URLs.
        """
        logger.info("Attempting to scrape from sitemap")
        
        # Fetch sitemap
        sitemap_content = self.fetch(self.sitemap_url, use_cache=False)
        if not sitemap_content:
            logger.error("Could not fetch sitemap")
            return []
        
        # Parse XML
        try:
            root = ET.fromstring(sitemap_content)
        except ET.ParseError:
            logger.error("Could not parse sitemap XML")
            return []
        
        # Extract URLs (handle namespaces)
        ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        urls = []
        
        for url_el in root.findall('.//sm:url/sm:loc', ns):
            url = url_el.text
            if url:
                # Filter to tool pages only
                path = urlparse(url).path.strip('/')
                if path and '/' not in path and len(path) < 100:
                    urls.append(url)
        
        # Also check for sitemap index (sitemaps of sitemaps)
        for sitemap_el in root.findall('.//sm:sitemap/sm:loc', ns):
            sub_url = sitemap_el.text
            if sub_url and 'tool' in sub_url.lower():
                sub_content = self.fetch(sub_url)
                if sub_content:
                    try:
                        sub_root = ET.fromstring(sub_content)
                        for url_el in sub_root.findall('.//sm:url/sm:loc', ns):
                            urls.append(url_el.text)
                    except ET.ParseError:
                        pass
        
        logger.info(f"Found {len(urls)} URLs in sitemap")
        
        if limit:
            urls = urls[:limit]
        
        # Scrape each tool page
        tools = []
        for i, url in enumerate(urls):
            logger.info(f"Scraping {i + 1}/{len(urls)}: {url}")
            
            html = self.fetch(url)
            if html:
                tool = self.parse_tool_page(html, url)
                if tool:
                    tools.append(tool)
        
        return tools
    
    def __exit__(self, *args):
        # Clean up Playwright
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        super().__exit__(*args)
