"""
Base Scraper Class
==================
This is the foundation for all our scrapers. It handles:
1. Rate limiting - Don't hammer websites (be polite!)
2. Retries - If a request fails, try again with backoff
3. Caching - Don't re-fetch pages we already have
4. robots.txt - Respect website rules
"""

import time
import hashlib
import json
import logging
from pathlib import Path
from typing import Optional
from abc import ABC, abstractmethod
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Prevents us from making too many requests too fast.
    
    WHY THIS MATTERS:
    - Websites will block you if you hit them too fast
    - It's polite to not overload their servers
    - Most sites expect 1-2 seconds between requests
    
    HOW IT WORKS:
    - Tracks the last request time for each domain
    - Waits if you try to request again too soon
    """
    
    def __init__(self, requests_per_second: float = 1.0):
        self.min_interval = 1.0 / requests_per_second  # Convert to seconds between requests
        self.last_request_time: dict[str, float] = {}  # domain -> timestamp
    
    def wait_if_needed(self, url: str) -> None:
        """Wait before making a request if we're going too fast."""
        domain = urlparse(url).netloc
        
        if domain in self.last_request_time:
            elapsed = time.time() - self.last_request_time[domain]
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s for {domain}")
                time.sleep(sleep_time)
        
        self.last_request_time[domain] = time.time()


class ResponseCache:
    """
    Caches HTTP responses to disk to avoid re-fetching.
    
    WHY THIS MATTERS:
    - If your script crashes, you don't lose all progress
    - Faster development (don't wait for network on every test)
    - Reduces load on target websites
    
    HOW IT WORKS:
    - Creates a hash of the URL
    - Saves response to a file named by that hash
    - Checks if file exists before making network request
    """
    
    def __init__(self, cache_dir: Path, ttl_hours: int = 24):
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_hours * 3600
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, url: str) -> Path:
        """Generate a unique filename for this URL."""
        # MD5 hash of URL = consistent filename
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self.cache_dir / f"{url_hash}.json"
    
    def get(self, url: str) -> Optional[str]:
        """Get cached response if it exists and isn't expired."""
        cache_path = self._get_cache_path(url)
        
        if not cache_path.exists():
            return None
        
        # Check if cache is expired
        age = time.time() - cache_path.stat().st_mtime
        if age > self.ttl_seconds:
            logger.debug(f"Cache expired for {url}")
            return None
        
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.debug(f"Cache hit for {url}")
            return data.get('content')
    
    def set(self, url: str, content: str) -> None:
        """Save response to cache."""
        cache_path = self._get_cache_path(url)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump({'url': url, 'content': content}, f)
        logger.debug(f"Cached response for {url}")


class RobotsChecker:
    """
    Checks robots.txt to see if we're allowed to scrape a URL.
    
    WHY THIS MATTERS:
    - robots.txt is a standard way websites say "don't scrape this"
    - Ignoring it can get you legally in trouble
    - It's the ethical thing to do
    
    HOW IT WORKS:
    - Fetches /robots.txt from each domain
    - Parses the rules
    - Checks each URL against those rules
    """
    
    def __init__(self):
        self.parsers: dict[str, RobotFileParser] = {}
    
    def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        """Check if we're allowed to fetch this URL."""
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        
        if domain not in self.parsers:
            parser = RobotFileParser()
            robots_url = f"{domain}/robots.txt"
            try:
                parser.set_url(robots_url)
                parser.read()
                self.parsers[domain] = parser
            except Exception as e:
                logger.warning(f"Could not fetch robots.txt for {domain}: {e}")
                # If we can't fetch robots.txt, assume we're allowed
                return True
        
        return self.parsers[domain].can_fetch(user_agent, url)


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers.
    
    TO CREATE A NEW SCRAPER:
    1. Inherit from this class
    2. Set `name` and `base_url` 
    3. Implement `parse_tool_list()` - get list of tool URLs
    4. Implement `parse_tool_page()` - extract tool data from a page
    
    The base class handles all the boring stuff (rate limiting, caching, etc.)
    """
    
    name: str = "base"  # Override in subclass
    base_url: str = ""  # Override in subclass
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        requests_per_second: float = 1.0,
        respect_robots: bool = True,
        max_retries: int = 3,
    ):
        # Set up cache directory (defaults to backend/cache/<scraper_name>)
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent / "cache" / self.name
        
        self.cache = ResponseCache(cache_dir)
        self.rate_limiter = RateLimiter(requests_per_second)
        self.robots_checker = RobotsChecker() if respect_robots else None
        self.max_retries = max_retries
        
        # HTTP client with browser-like headers
        self.client = httpx.Client(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            },
            timeout=30.0,
            follow_redirects=True,
        )
        
        logger.info(f"Initialized {self.name} scraper")
    
    def fetch(self, url: str, use_cache: bool = True) -> Optional[str]:
        """
        Fetch a URL with caching, rate limiting, and retries.
        
        This is the main method you'll use to get web pages.
        It handles all the complexity for you.
        """
        # Check robots.txt
        if self.robots_checker and not self.robots_checker.can_fetch(url):
            logger.warning(f"robots.txt disallows: {url}")
            return None
        
        # Check cache first
        if use_cache:
            cached = self.cache.get(url)
            if cached:
                return cached
        
        # Rate limit before request
        self.rate_limiter.wait_if_needed(url)
        
        # Try to fetch with retries
        for attempt in range(self.max_retries):
            try:
                response = self.client.get(url)
                response.raise_for_status()
                content = response.text
                
                # Cache the successful response
                if use_cache:
                    self.cache.set(url, content)
                
                return content
                
            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP {e.response.status_code} for {url} (attempt {attempt + 1})")
                if e.response.status_code == 429:  # Too Many Requests
                    time.sleep(60)  # Wait a minute before retrying
                elif e.response.status_code >= 500:  # Server error
                    time.sleep(5 * (attempt + 1))  # Exponential backoff
                else:
                    break  # Client error, don't retry
                    
            except httpx.RequestError as e:
                logger.warning(f"Request failed for {url}: {e} (attempt {attempt + 1})")
                time.sleep(5 * (attempt + 1))
        
        logger.error(f"Failed to fetch {url} after {self.max_retries} attempts")
        return None
    
    @abstractmethod
    def parse_tool_list(self, html: str) -> list[str]:
        """
        Parse the main listing page and return URLs of individual tool pages.
        
        IMPLEMENT THIS: Return a list of URLs to tool detail pages.
        """
        pass
    
    @abstractmethod
    def parse_tool_page(self, html: str, url: str) -> Optional[dict]:
        """
        Parse an individual tool page and extract tool data.
        
        IMPLEMENT THIS: Return a dict matching the schema in schema.md
        """
        pass
    
    def scrape_all(self, limit: Optional[int] = None) -> list[dict]:
        """
        Main entry point: scrape all tools from this source.
        
        Args:
            limit: Max number of tools to scrape (for testing)
        
        Returns:
            List of tool dictionaries matching our schema
        """
        logger.info(f"Starting scrape of {self.name}")
        tools = []
        
        # Step 1: Get the main listing page
        html = self.fetch(self.base_url)
        if not html:
            logger.error(f"Could not fetch main page: {self.base_url}")
            return tools
        
        # Step 2: Parse out individual tool URLs
        tool_urls = self.parse_tool_list(html)
        logger.info(f"Found {len(tool_urls)} tool URLs")
        
        if limit:
            tool_urls = tool_urls[:limit]
        
        # Step 3: Fetch and parse each tool page
        for i, url in enumerate(tool_urls):
            logger.info(f"Scraping tool {i + 1}/{len(tool_urls)}: {url}")
            
            html = self.fetch(url)
            if not html:
                continue
            
            tool_data = self.parse_tool_page(html, url)
            if tool_data:
                tools.append(tool_data)
        
        logger.info(f"Scraped {len(tools)} tools from {self.name}")
        return tools
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.client.close()
