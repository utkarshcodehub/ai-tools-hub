"""
New Tool Monitors
=================
Monitors various sources for newly launched AI tools.

SOURCES:
1. Hacker News - Uses Algolia API (free, no auth needed)
2. GitHub - Uses GitHub API (free, optional auth for higher limits)

WHY MONITORING:
- Catch new tools as they launch
- Stay ahead of competitors
- Build comprehensive directory

USAGE:
    from scrapers.monitors import HackerNewsMonitor, GitHubMonitor
    
    # Get recent AI tools from HN
    hn = HackerNewsMonitor()
    tools = hn.get_recent_launches(days=7)
    
    # Get trending AI repos from GitHub
    gh = GitHubMonitor()
    tools = gh.get_trending_ai_repos()
"""

import re
import os
import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class HackerNewsMonitor:
    """
    Monitors Hacker News for AI tool launches.
    
    Uses Algolia's free HN Search API:
    https://hn.algolia.com/api
    
    STRATEGY:
    - Search for "Show HN" posts with AI keywords
    - Filter by date and vote count
    - Extract tool URLs and descriptions
    """
    
    API_URL = "https://hn.algolia.com/api/v1"
    
    # Keywords that indicate an AI tool
    AI_KEYWORDS = [
        "AI", "GPT", "LLM", "ChatGPT", "Claude", "Gemini",
        "machine learning", "ML", "neural", "transformer",
        "image generation", "text-to-image", "text-to-speech",
        "voice clone", "AI assistant", "copilot", "agent",
        "RAG", "embedding", "vector", "generative"
    ]
    
    def __init__(self):
        self.client = httpx.Client(timeout=30.0)
    
    def get_recent_launches(
        self, 
        days: int = 7, 
        min_points: int = 10,
        limit: int = 50
    ) -> list[dict]:
        """
        Get recent AI tool launches from Hacker News.
        
        Args:
            days: How far back to look
            min_points: Minimum upvotes (filters noise)
            limit: Max results
        
        Returns:
            List of tool dicts matching our schema
        """
        tools = []
        seen_urls = set()
        
        # Search for each AI keyword
        for keyword in self.AI_KEYWORDS[:5]:  # Limit to avoid too many requests
            query = f'"Show HN" {keyword}'
            
            params = {
                "query": query,
                "tags": "story",
                "numericFilters": f"points>={min_points},created_at_i>={self._days_ago_timestamp(days)}",
                "hitsPerPage": 20,
            }
            
            try:
                response = self.client.get(f"{self.API_URL}/search", params=params)
                response.raise_for_status()
                data = response.json()
                
                for hit in data.get('hits', []):
                    tool = self._hit_to_tool(hit)
                    if tool and tool['website'] not in seen_urls:
                        seen_urls.add(tool['website'])
                        tools.append(tool)
                        
            except httpx.RequestError as e:
                logger.error(f"HN API error: {e}")
                continue
        
        # Sort by points (popularity)
        tools.sort(key=lambda x: x.get('_points', 0), reverse=True)
        
        # Remove internal fields
        for tool in tools:
            tool.pop('_points', None)
            tool.pop('_hn_id', None)
        
        logger.info(f"Found {len(tools)} AI tools from Hacker News")
        return tools[:limit]
    
    def _hit_to_tool(self, hit: dict) -> Optional[dict]:
        """Convert HN search hit to our tool schema."""
        title = hit.get('title', '')
        url = hit.get('url', '')
        
        # Skip if no URL (text-only posts)
        if not url:
            # Try to extract URL from story
            story_url = f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            url = story_url
        
        # Extract tool name from title
        # "Show HN: ToolName – Description" or "Show HN: ToolName - Description"
        name_match = re.match(r'Show HN:\s*([^–\-:]+)', title)
        if name_match:
            name = name_match.group(1).strip()
        else:
            name = title[:50]
        
        # Extract description
        description = title.replace('Show HN:', '').strip()
        if '–' in description:
            description = description.split('–', 1)[1].strip()
        elif '-' in description:
            description = description.split('-', 1)[1].strip()
        
        return {
            'name': name,
            'tagline': description[:80] if description else f"{name} - AI tool",
            'website': url,
            'categories': self._guess_categories(title + ' ' + description),
            'tags': ['hacker-news', 'new-launch'],
            'pricing': {'has_free_tier': False},
            'api': {'available': False},
            'status': 'active',
            '_points': hit.get('points', 0),
            '_hn_id': hit.get('objectID'),
        }
    
    def _guess_categories(self, text: str) -> list[str]:
        """Guess categories based on text content."""
        text_lower = text.lower()
        categories = []
        
        category_keywords = {
            'llm': ['llm', 'gpt', 'chatgpt', 'claude', 'chat', 'language model'],
            'code': ['code', 'coding', 'developer', 'programming', 'github', 'ide'],
            'image': ['image', 'art', 'design', 'picture', 'photo', 'midjourney', 'dall-e'],
            'video': ['video', 'movie', 'animation'],
            'audio': ['audio', 'music', 'sound'],
            'speech': ['voice', 'speech', 'transcri', 'tts', 'stt'],
            'search': ['search', 'research', 'rag'],
            'agents': ['agent', 'automat', 'workflow'],
            'productivity': ['writing', 'note', 'email', 'productivity'],
        }
        
        for cat, keywords in category_keywords.items():
            if any(kw in text_lower for kw in keywords):
                categories.append(cat)
        
        return categories if categories else ['llm']  # Default
    
    def _days_ago_timestamp(self, days: int) -> int:
        """Get Unix timestamp for N days ago."""
        return int((datetime.utcnow() - timedelta(days=days)).timestamp())
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.client.close()


class GitHubMonitor:
    """
    Monitors GitHub for trending AI repositories.
    
    Uses GitHub Search API:
    https://docs.github.com/en/rest/search
    
    STRATEGY:
    - Search for repos with AI/ML topics
    - Filter by recent creation date
    - Sort by stars
    """
    
    API_URL = "https://api.github.com"
    
    # Topics that indicate AI tools
    AI_TOPICS = [
        "artificial-intelligence", "machine-learning", "deep-learning",
        "llm", "gpt", "chatgpt", "langchain", "ai-tools",
        "generative-ai", "text-generation", "image-generation"
    ]
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub monitor.
        
        Args:
            token: GitHub personal access token (optional, increases rate limit)
        """
        self.token = token or os.environ.get('GITHUB_TOKEN')
        
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        
        self.client = httpx.Client(headers=headers, timeout=30.0)
    
    def get_trending_ai_repos(
        self, 
        days: int = 30,
        min_stars: int = 50,
        limit: int = 50
    ) -> list[dict]:
        """
        Get trending AI repositories from GitHub.
        
        Args:
            days: Repos created within this many days
            min_stars: Minimum star count
            limit: Max results
        
        Returns:
            List of tool dicts matching our schema
        """
        tools = []
        seen_repos = set()
        
        # Calculate date threshold
        date_threshold = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Search for AI-related repos
        for topic in self.AI_TOPICS[:3]:  # Limit to avoid rate limits
            query = f"topic:{topic} stars:>={min_stars} created:>={date_threshold}"
            
            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": 20,
            }
            
            try:
                response = self.client.get(f"{self.API_URL}/search/repositories", params=params)
                
                if response.status_code == 403:
                    logger.warning("GitHub rate limit hit. Set GITHUB_TOKEN for higher limits.")
                    break
                
                response.raise_for_status()
                data = response.json()
                
                for repo in data.get('items', []):
                    full_name = repo.get('full_name', '')
                    if full_name not in seen_repos:
                        seen_repos.add(full_name)
                        tool = self._repo_to_tool(repo)
                        if tool:
                            tools.append(tool)
                            
            except httpx.RequestError as e:
                logger.error(f"GitHub API error: {e}")
                continue
        
        # Sort by stars
        tools.sort(key=lambda x: x.get('_stars', 0), reverse=True)
        
        # Remove internal fields
        for tool in tools:
            tool.pop('_stars', None)
        
        logger.info(f"Found {len(tools)} AI tools from GitHub")
        return tools[:limit]
    
    def _repo_to_tool(self, repo: dict) -> Optional[dict]:
        """Convert GitHub repo to our tool schema."""
        name = repo.get('name', '')
        description = repo.get('description', '') or ''
        
        # Skip forks
        if repo.get('fork'):
            return None
        
        # Website: prefer homepage, fall back to GitHub URL
        website = repo.get('homepage') or repo.get('html_url', '')
        
        # Guess categories from topics and description
        topics = repo.get('topics', [])
        categories = self._topics_to_categories(topics, description)
        
        return {
            'name': name.replace('-', ' ').replace('_', ' ').title(),
            'tagline': description[:80] if description else f"{name} - Open source AI tool",
            'website': website,
            'categories': categories,
            'tags': ['open-source', 'github'] + topics[:3],
            'pricing': {
                'has_free_tier': True,  # Open source = free
                'free_details': 'Open source',
            },
            'api': {
                'available': True,  # Repos usually have APIs
                'docs_url': f"{repo.get('html_url')}/blob/main/README.md",
            },
            'status': 'active',
            '_stars': repo.get('stargazers_count', 0),
        }
    
    def _topics_to_categories(self, topics: list[str], description: str) -> list[str]:
        """Convert GitHub topics to our categories."""
        text = ' '.join(topics) + ' ' + description.lower()
        categories = []
        
        mapping = {
            'llm': ['llm', 'gpt', 'language-model', 'chatbot', 'chat'],
            'code': ['code', 'coding', 'ide', 'developer-tools'],
            'image': ['image', 'stable-diffusion', 'diffusion', 'text-to-image'],
            'video': ['video', 'text-to-video'],
            'audio': ['audio', 'music', 'sound'],
            'speech': ['speech', 'voice', 'tts', 'stt', 'whisper'],
            'search': ['search', 'retrieval', 'rag'],
            'agents': ['agent', 'langchain', 'autogpt', 'automation'],
            'embeddings': ['embedding', 'vector', 'similarity'],
        }
        
        for cat, keywords in mapping.items():
            if any(kw in text for kw in keywords):
                categories.append(cat)
        
        return categories if categories else ['llm']
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.client.close()


def discover_new_tools(days: int = 7, min_points: int = 20) -> list[dict]:
    """
    Convenience function to discover new AI tools from all sources.
    
    Returns combined, deduplicated list of new tools.
    """
    all_tools = []
    
    # Hacker News
    with HackerNewsMonitor() as hn:
        hn_tools = hn.get_recent_launches(days=days, min_points=min_points)
        all_tools.extend(hn_tools)
        logger.info(f"HN: {len(hn_tools)} tools")
    
    # GitHub
    with GitHubMonitor() as gh:
        gh_tools = gh.get_trending_ai_repos(days=days * 4, min_stars=100)
        all_tools.extend(gh_tools)
        logger.info(f"GitHub: {len(gh_tools)} tools")
    
    return all_tools
