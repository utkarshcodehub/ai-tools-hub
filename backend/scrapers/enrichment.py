"""
Enrichment Module
=================
Takes basic scraped tool data and enriches it with:
1. Pricing information (by scraping pricing pages)
2. API documentation detection
3. Logo URLs (via Clearbit or direct)
4. Better taglines (via LLM)

WHY ENRICHMENT:
- Scraped data is often incomplete
- Different sources have different levels of detail
- We want consistent, rich data for all tools
"""

import re
import logging
from typing import Optional
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ToolEnricher:
    """
    Enriches tool data with additional information.
    
    USAGE:
        enricher = ToolEnricher()
        
        # Enrich a single tool
        enriched = enricher.enrich(tool)
        
        # Enrich many tools in parallel
        enriched_tools = enricher.enrich_batch(tools, max_workers=5)
    """
    
    def __init__(self, timeout: float = 15.0):
        self.client = httpx.Client(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            timeout=timeout,
            follow_redirects=True,
        )
    
    def enrich(self, tool: dict, skip_existing: bool = True) -> dict:
        """
        Enrich a single tool with additional data.
        
        Args:
            tool: Tool dictionary to enrich
            skip_existing: Don't overwrite existing data
        
        Returns:
            Enriched tool dictionary
        """
        result = dict(tool)  # Copy
        website = tool.get('website', '')
        
        if not website:
            return result
        
        # Enrich logo
        if not result.get('logo_url') or not skip_existing:
            result['logo_url'] = self._get_logo_url(website)
        
        # Enrich pricing
        pricing = result.get('pricing', {})
        if not pricing.get('pricing_url') or not skip_existing:
            pricing_info = self._detect_pricing(website)
            result['pricing'] = {**pricing, **pricing_info}
        
        # Enrich API info
        api = result.get('api', {})
        if not api.get('docs_url') or not skip_existing:
            api_info = self._detect_api(website)
            result['api'] = {**api, **api_info}
        
        return result
    
    def enrich_batch(
        self, 
        tools: list[dict], 
        max_workers: int = 5,
        skip_existing: bool = True
    ) -> list[dict]:
        """
        Enrich multiple tools in parallel.
        
        Args:
            tools: List of tool dictionaries
            max_workers: Number of parallel threads
            skip_existing: Don't overwrite existing data
        
        Returns:
            List of enriched tools
        """
        enriched = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.enrich, tool, skip_existing): i 
                for i, tool in enumerate(tools)
            }
            
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    result = future.result()
                    enriched.append((idx, result))
                except Exception as e:
                    logger.error(f"Enrichment failed for tool {idx}: {e}")
                    enriched.append((idx, tools[idx]))
        
        # Sort by original index to maintain order
        enriched.sort(key=lambda x: x[0])
        return [tool for _, tool in enriched]
    
    def _get_logo_url(self, website: str) -> str:
        """
        Get logo URL for a website.
        
        STRATEGY:
        1. Try Clearbit Logo API (free, high quality)
        2. Fall back to favicon if Clearbit fails
        """
        domain = urlparse(website).netloc
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Clearbit gives nice square logos
        return f"https://logo.clearbit.com/{domain}"
    
    def _detect_pricing(self, website: str) -> dict:
        """
        Try to find and parse pricing information.
        
        STRATEGY:
        1. Look for /pricing, /plans, /price pages
        2. Parse the page for pricing keywords
        3. Detect free tier indicators
        """
        result = {
            'has_free_tier': False,
            'free_details': None,
            'paid_starts_at': None,
            'pricing_url': None,
        }
        
        # Common pricing page paths
        pricing_paths = ['/pricing', '/plans', '/price', '/prices', '/subscribe']
        base_url = self._get_base_url(website)
        
        for path in pricing_paths:
            url = urljoin(base_url, path)
            try:
                response = self.client.get(url)
                if response.status_code == 200:
                    result['pricing_url'] = url
                    
                    # Parse pricing info from page
                    pricing_data = self._parse_pricing_page(response.text)
                    result.update(pricing_data)
                    
                    logger.debug(f"Found pricing at {url}")
                    break
                    
            except httpx.RequestError:
                continue
        
        return result
    
    def _parse_pricing_page(self, html: str) -> dict:
        """
        Extract pricing information from HTML.
        
        Looks for:
        - "Free" tier mentions
        - Price amounts ($X/mo, $X/year)
        - Plan names (Starter, Pro, Enterprise)
        """
        result = {
            'has_free_tier': False,
            'free_details': None,
            'paid_starts_at': None,
        }
        
        soup = BeautifulSoup(html, 'lxml')
        text = soup.get_text(separator=' ', strip=True).lower()
        
        # Detect free tier
        free_patterns = [
            r'free\s*(plan|tier|forever|trial)?',
            r'\$0',
            r'no credit card',
            r'get started free',
            r'start for free',
        ]
        
        for pattern in free_patterns:
            if re.search(pattern, text):
                result['has_free_tier'] = True
                break
        
        # Try to extract free tier details
        if result['has_free_tier']:
            # Look for context around "free"
            free_match = re.search(r'free[^.]{0,100}', text)
            if free_match:
                result['free_details'] = free_match.group(0)[:80].strip()
        
        # Extract lowest price
        price_patterns = [
            r'\$(\d+(?:\.\d{2})?)\s*/?(?:mo|month|m)',  # $X/mo
            r'\$(\d+(?:\.\d{2})?)\s*/?(?:yr|year|y)',   # $X/year
            r'(\d+(?:\.\d{2})?)\s*(?:USD|€|£)\s*/?(?:mo|month)', # X USD/mo
        ]
        
        prices = []
        for pattern in price_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    price = float(match)
                    if 0 < price < 10000:  # Sanity check
                        prices.append(price)
                except ValueError:
                    continue
        
        if prices:
            min_price = min(prices)
            if '/y' in text or '/year' in text:
                result['paid_starts_at'] = f"${min_price}/year"
            else:
                result['paid_starts_at'] = f"${min_price}/mo"
        
        return result
    
    def _detect_api(self, website: str) -> dict:
        """
        Try to find API documentation.
        
        STRATEGY:
        1. Check common API doc paths
        2. Look for developer/docs subdomain
        3. Check for API mentions on main page
        """
        result = {
            'available': False,
            'docs_url': None,
            'key_url': None,
        }
        
        base_url = self._get_base_url(website)
        domain = urlparse(website).netloc
        
        # Common API documentation paths
        api_paths = [
            '/docs', '/api', '/developers', '/api-docs',
            '/documentation', '/api/docs', '/developer',
            '/reference', '/api-reference'
        ]
        
        # Also try subdomains
        api_subdomains = [
            f"https://docs.{domain}",
            f"https://api.{domain}",
            f"https://developer.{domain}",
            f"https://developers.{domain}",
        ]
        
        # Check paths first
        for path in api_paths:
            url = urljoin(base_url, path)
            try:
                response = self.client.head(url)
                if response.status_code == 200:
                    result['available'] = True
                    result['docs_url'] = url
                    logger.debug(f"Found API docs at {url}")
                    break
            except httpx.RequestError:
                continue
        
        # If not found, try subdomains
        if not result['available']:
            for url in api_subdomains:
                try:
                    response = self.client.head(url)
                    if response.status_code == 200:
                        result['available'] = True
                        result['docs_url'] = url
                        logger.debug(f"Found API docs at {url}")
                        break
                except httpx.RequestError:
                    continue
        
        # Try to find API key signup page
        if result['available']:
            key_paths = ['/api-keys', '/keys', '/credentials', '/console', '/dashboard']
            for path in key_paths:
                url = urljoin(base_url, path)
                try:
                    response = self.client.head(url)
                    if response.status_code in (200, 302):  # 302 = redirect to login
                        result['key_url'] = url
                        break
                except httpx.RequestError:
                    continue
        
        return result
    
    def _get_base_url(self, url: str) -> str:
        """Extract base URL (scheme + domain) from full URL."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.client.close()


class LLMEnricher:
    """
    Uses LLM to generate/improve tool descriptions.
    
    REQUIRES: GOOGLE_API_KEY environment variable (for Gemini)
    
    WHY LLM:
    - Scraped taglines are inconsistent in style
    - Some tools have no description at all
    - LLM can generate consistent, useful summaries
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize with Gemini API key.
        
        Get free key at: https://makersuite.google.com/app/apikey
        """
        import os
        self.api_key = api_key or os.environ.get('GOOGLE_API_KEY')
        
        if not self.api_key:
            logger.warning(
                "No Gemini API key. Set GOOGLE_API_KEY env var. "
                "Get free key at: https://makersuite.google.com/app/apikey"
            )
        
        self.client = httpx.Client(timeout=30.0)
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    
    def generate_tagline(self, name: str, website: str, existing_tagline: str = "") -> Optional[str]:
        """
        Generate a concise, consistent tagline for a tool.
        
        Args:
            name: Tool name
            website: Tool website
            existing_tagline: Current tagline (if any)
        
        Returns:
            New tagline (max 80 chars) or None if failed
        """
        if not self.api_key:
            return None
        
        prompt = f"""Generate a concise tagline (max 80 characters) for this AI tool.

Tool: {name}
Website: {website}
Current description: {existing_tagline or 'None'}

Requirements:
- Maximum 80 characters
- Start with a verb or describe what it does
- Be specific about the AI capability
- No marketing fluff
- No quotes around the response

Example good taglines:
- "AI code assistant for faster development"
- "Generate images from text descriptions"
- "Transcribe audio to text with high accuracy"

Respond with ONLY the tagline, nothing else."""

        try:
            response = self.client.post(
                f"{self.api_url}?key={self.api_key}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": 50}
                }
            )
            response.raise_for_status()
            
            data = response.json()
            text = data['candidates'][0]['content']['parts'][0]['text']
            
            # Clean up response
            tagline = text.strip().strip('"\'')
            
            # Enforce max length
            if len(tagline) > 80:
                tagline = tagline[:77] + "..."
            
            return tagline
            
        except Exception as e:
            logger.error(f"LLM tagline generation failed: {e}")
            return None
    
    def categorize_tool(self, name: str, tagline: str, website: str) -> list[str]:
        """
        Use LLM to suggest categories for a tool.
        
        Returns list of category IDs from our fixed list.
        """
        if not self.api_key:
            return []
        
        prompt = f"""Categorize this AI tool into one or more categories.

Tool: {name}
Description: {tagline}
Website: {website}

Available categories (use ONLY these exact IDs):
- llm: Large language models and chatbots
- code: Coding assistants and developer tools
- image: Image generation and editing
- video: Video generation and editing
- audio: Music and sound generation
- speech: Speech-to-text and text-to-speech
- search: AI search engines and research tools
- agents: AI agents and automation
- embeddings: Vector embeddings and RAG
- productivity: Writing, notes, and workflows

Respond with a comma-separated list of category IDs only.
Example: llm, code, productivity"""

        try:
            response = self.client.post(
                f"{self.api_url}?key={self.api_key}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": 50}
                }
            )
            response.raise_for_status()
            
            data = response.json()
            text = data['candidates'][0]['content']['parts'][0]['text']
            
            # Parse comma-separated categories
            valid_cats = {'llm', 'code', 'image', 'video', 'audio', 'speech', 
                         'search', 'agents', 'embeddings', 'productivity'}
            
            categories = []
            for cat in text.lower().replace(' ', '').split(','):
                cat = cat.strip()
                if cat in valid_cats and cat not in categories:
                    categories.append(cat)
            
            return categories
            
        except Exception as e:
            logger.error(f"LLM categorization failed: {e}")
            return []
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.client.close()
