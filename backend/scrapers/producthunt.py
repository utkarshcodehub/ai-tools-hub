"""
ProductHunt API Scraper
=======================
Fetches AI tools from ProductHunt using their official GraphQL API.

WHY PRODUCTHUNT:
- Official API (no blocking issues)
- High-quality data (descriptions, votes, comments)
- Great for discovering NEW tools (daily launches)
- Community validation (upvotes indicate quality)

API SETUP:
1. Go to https://www.producthunt.com/v2/oauth/applications
2. Create an application to get client credentials
3. Set PH_API_KEY environment variable

NOTE: ProductHunt uses GraphQL, not REST.
"""

import os
import logging
from typing import Optional
from datetime import datetime, timedelta

import httpx

logger = logging.getLogger(__name__)


class ProductHuntScraper:
    """
    Fetches AI tools from ProductHunt's GraphQL API.
    
    USAGE:
        scraper = ProductHuntScraper(api_key="your_key")
        # OR set PH_API_KEY environment variable
        
        # Get today's AI launches
        tools = scraper.get_ai_launches(days_back=1)
        
        # Get top AI products of all time
        tools = scraper.search_ai_tools(limit=100)
    """
    
    API_URL = "https://api.producthunt.com/v2/api/graphql"
    
    # ProductHunt topics related to AI
    AI_TOPICS = [
        "artificial-intelligence",
        "machine-learning", 
        "chatgpt",
        "generative-ai",
        "ai-tools",
        "llm",
        "gpt",
        "ai-assistant",
        "ai-chatbot",
    ]
    
    # Map ProductHunt topics to our categories
    TOPIC_TO_CATEGORY = {
        "artificial-intelligence": "llm",
        "machine-learning": "llm",
        "chatgpt": "llm",
        "generative-ai": "image",
        "ai-tools": "productivity",
        "llm": "llm",
        "gpt": "llm",
        "ai-assistant": "agents",
        "ai-chatbot": "llm",
        "developer-tools": "code",
        "design-tools": "image",
        "writing-tools": "productivity",
        "video": "video",
        "music": "audio",
        "voice": "speech",
        "search": "search",
        "automation": "agents",
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize with API key.
        
        Get your key at: https://www.producthunt.com/v2/oauth/applications
        """
        self.api_key = api_key or os.environ.get('PH_API_KEY')
        
        if not self.api_key:
            logger.warning(
                "No ProductHunt API key provided. "
                "Set PH_API_KEY environment variable or pass api_key parameter. "
                "Get your key at: https://www.producthunt.com/v2/oauth/applications"
            )
        
        self.client = httpx.Client(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
    
    def _query(self, query: str, variables: dict = None) -> Optional[dict]:
        """Execute a GraphQL query."""
        if not self.api_key:
            logger.error("Cannot query ProductHunt without API key")
            return None
        
        try:
            response = self.client.post(
                self.API_URL,
                json={"query": query, "variables": variables or {}}
            )
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                logger.error(f"GraphQL errors: {data['errors']}")
                return None
            
            return data.get("data")
            
        except httpx.HTTPError as e:
            logger.error(f"ProductHunt API error: {e}")
            return None
    
    def get_ai_launches(self, days_back: int = 7, limit: int = 50) -> list[dict]:
        """
        Get recent AI tool launches.
        
        Args:
            days_back: How many days back to look
            limit: Maximum number of results
        
        Returns:
            List of tool dicts matching our schema
        """
        # GraphQL query for posts with AI topics
        query = """
        query GetPosts($topic: String!, $first: Int!, $postedAfter: DateTime) {
            posts(
                topic: $topic,
                first: $first,
                postedAfter: $postedAfter,
                order: VOTES
            ) {
                edges {
                    node {
                        id
                        name
                        tagline
                        description
                        url
                        website
                        votesCount
                        createdAt
                        thumbnail {
                            url
                        }
                        topics {
                            edges {
                                node {
                                    slug
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        # Calculate date threshold
        posted_after = (datetime.utcnow() - timedelta(days=days_back)).isoformat() + "Z"
        
        all_tools = []
        seen_ids = set()
        
        # Query each AI topic
        for topic in self.AI_TOPICS:
            logger.info(f"Querying ProductHunt topic: {topic}")
            
            data = self._query(query, {
                "topic": topic,
                "first": min(limit, 50),  # PH limit per request
                "postedAfter": posted_after,
            })
            
            if not data:
                continue
            
            posts = data.get("posts", {}).get("edges", [])
            
            for edge in posts:
                post = edge.get("node", {})
                post_id = post.get("id")
                
                # Skip duplicates (same product can be in multiple topics)
                if post_id in seen_ids:
                    continue
                seen_ids.add(post_id)
                
                tool = self._post_to_tool(post)
                if tool:
                    all_tools.append(tool)
        
        # Sort by votes (popularity)
        all_tools.sort(key=lambda x: x.get('_votes', 0), reverse=True)
        
        # Remove internal _votes field
        for tool in all_tools:
            tool.pop('_votes', None)
        
        logger.info(f"Found {len(all_tools)} AI tools from ProductHunt")
        return all_tools[:limit]
    
    def search_ai_tools(self, search_term: str = "AI", limit: int = 50) -> list[dict]:
        """
        Search for AI tools by keyword.
        
        Args:
            search_term: Search query
            limit: Maximum results
        
        Returns:
            List of tool dicts
        """
        query = """
        query SearchPosts($query: String!, $first: Int!) {
            posts(first: $first, order: RANKING, topic: "artificial-intelligence") {
                edges {
                    node {
                        id
                        name
                        tagline
                        description
                        url
                        website
                        votesCount
                        thumbnail {
                            url
                        }
                        topics {
                            edges {
                                node {
                                    slug
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        data = self._query(query, {"query": search_term, "first": min(limit, 50)})
        
        if not data:
            return []
        
        tools = []
        for edge in data.get("posts", {}).get("edges", []):
            post = edge.get("node", {})
            tool = self._post_to_tool(post)
            if tool:
                tools.append(tool)
        
        return tools
    
    def _post_to_tool(self, post: dict) -> Optional[dict]:
        """Convert ProductHunt post to our tool schema."""
        if not post.get("name"):
            return None
        
        # Extract categories from topics
        categories = []
        topics = post.get("topics", {}).get("edges", [])
        for topic_edge in topics:
            topic_slug = topic_edge.get("node", {}).get("slug", "")
            if topic_slug in self.TOPIC_TO_CATEGORY:
                cat = self.TOPIC_TO_CATEGORY[topic_slug]
                if cat not in categories:
                    categories.append(cat)
        
        # Use "llm" as default if no category matched
        if not categories:
            categories = ["llm"]
        
        # Get logo from thumbnail
        thumbnail = post.get("thumbnail", {})
        logo_url = thumbnail.get("url") if thumbnail else None
        
        # Website is preferred, fall back to ProductHunt URL
        website = post.get("website") or post.get("url") or ""
        
        return {
            'name': post.get("name"),
            'tagline': (post.get("tagline") or "")[:80],
            'website': website,
            'logo_url': logo_url,
            'categories': categories,
            'tags': ['producthunt', 'trending'],
            'pricing': {
                'has_free_tier': False,  # We don't know from PH data
            },
            'api': {
                'available': False,  # We don't know from PH data
            },
            'status': 'active',
            '_votes': post.get("votesCount", 0),  # Temp field for sorting
        }
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.client.close()
