"""
Schema Validator
================
Validates scraped tool data against our schema before adding to the database.

WHY THIS MATTERS:
- Scraped data is messy - missing fields, wrong types, weird values
- We need consistent data for the frontend to work
- Catches problems early before they break things

VALIDATION RULES:
- Required fields must exist
- URLs must be valid format
- Categories must be from our fixed list
- Pricing fields have specific formats
"""

import re
import logging
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Our fixed categories from schema.md
VALID_CATEGORIES = {
    "llm", "code", "image", "video", "audio", 
    "search", "agents", "embeddings", "speech", "productivity"
}

# Valid status values
VALID_STATUSES = {"active", "beta", "deprecated"}

# Valid auth methods
VALID_AUTH_METHODS = {"Bearer", "x-api-key", "Basic", "query-param", "none"}


def is_valid_url(url: str) -> bool:
    """Check if a string is a valid URL."""
    if not url:
        return False
    try:
        result = urlparse(url)
        return all([result.scheme in ('http', 'https'), result.netloc])
    except Exception:
        return False


def slugify(text: str) -> str:
    """
    Convert text to kebab-case slug for IDs.
    
    Examples:
        "GPT-4o" -> "gpt-4o"
        "Claude 3.5 Sonnet" -> "claude-3-5-sonnet"
        "DALL·E 3" -> "dall-e-3"
    """
    # Lowercase
    text = text.lower()
    # Replace special chars with hyphen
    text = re.sub(r'[·•]', '-', text)
    # Replace spaces and underscores with hyphen
    text = re.sub(r'[\s_]+', '-', text)
    # Remove anything that's not alphanumeric or hyphen
    text = re.sub(r'[^a-z0-9-]', '', text)
    # Remove multiple consecutive hyphens
    text = re.sub(r'-+', '-', text)
    # Remove leading/trailing hyphens
    text = text.strip('-')
    return text


class ToolValidator:
    """
    Validates and normalizes tool data.
    
    USAGE:
        validator = ToolValidator()
        valid_tool = validator.validate(raw_tool_data)
        if valid_tool:
            # Data is clean and ready to use
        else:
            # Data was invalid, check logs for why
    """
    
    def __init__(self, strict: bool = False):
        """
        Args:
            strict: If True, reject tools with any missing optional fields.
                   If False (default), fill in sensible defaults.
        """
        self.strict = strict
        self.errors: list[str] = []
        self.warnings: list[str] = []
    
    def validate(self, data: dict) -> Optional[dict]:
        """
        Validate and normalize a tool dictionary.
        
        Returns the cleaned data, or None if validation failed.
        """
        self.errors = []
        self.warnings = []
        
        # Make a copy so we don't modify the original
        tool = dict(data)
        
        # === REQUIRED FIELDS ===
        
        # Name (required)
        if not tool.get('name'):
            self.errors.append("Missing required field: name")
            return None
        tool['name'] = str(tool['name']).strip()
        
        # Generate ID from name if missing
        if not tool.get('id'):
            tool['id'] = slugify(tool['name'])
            self.warnings.append(f"Generated ID from name: {tool['id']}")
        else:
            tool['id'] = slugify(tool['id'])
        
        # Website (required)
        if not tool.get('website'):
            self.errors.append("Missing required field: website")
            return None
        if not is_valid_url(tool['website']):
            self.errors.append(f"Invalid website URL: {tool['website']}")
            return None
        
        # === RECOMMENDED FIELDS ===
        
        # Tagline
        if not tool.get('tagline'):
            tool['tagline'] = f"{tool['name']} - AI tool"
            self.warnings.append("Generated placeholder tagline")
        else:
            # Truncate to 80 chars per schema
            tool['tagline'] = str(tool['tagline'])[:80].strip()
        
        # Logo URL - use Clearbit if missing
        if not tool.get('logo_url'):
            domain = urlparse(tool['website']).netloc
            tool['logo_url'] = f"https://logo.clearbit.com/{domain}"
            self.warnings.append(f"Generated logo URL via Clearbit: {tool['logo_url']}")
        
        # Categories - validate against fixed list
        if not tool.get('categories'):
            tool['categories'] = []
            self.warnings.append("No categories specified")
        else:
            valid_cats = [c for c in tool['categories'] if c in VALID_CATEGORIES]
            invalid_cats = [c for c in tool['categories'] if c not in VALID_CATEGORIES]
            if invalid_cats:
                self.warnings.append(f"Removed invalid categories: {invalid_cats}")
            tool['categories'] = valid_cats
        
        # Tags - freeform, just ensure it's a list
        if not tool.get('tags'):
            tool['tags'] = []
        tool['tags'] = [str(t).lower().strip() for t in tool['tags'] if t]
        
        # === PRICING SECTION ===
        tool['pricing'] = self._validate_pricing(tool.get('pricing', {}))
        
        # === API SECTION ===
        tool['api'] = self._validate_api(tool.get('api', {}))
        
        # === OTHER FIELDS ===
        
        # Free alternatives - ensure list of strings
        if not tool.get('free_alternatives'):
            tool['free_alternatives'] = []
        tool['free_alternatives'] = [slugify(str(a)) for a in tool['free_alternatives'] if a]
        
        # Status
        if not tool.get('status'):
            tool['status'] = 'active'
        elif tool['status'] not in VALID_STATUSES:
            self.warnings.append(f"Invalid status '{tool['status']}', defaulting to 'active'")
            tool['status'] = 'active'
        
        # Verified date - should be YYYY-MM-DD
        if tool.get('free_tier_verified_date'):
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', tool['free_tier_verified_date']):
                self.warnings.append("Invalid date format, clearing free_tier_verified_date")
                tool['free_tier_verified_date'] = None
        
        # Log any issues
        if self.errors:
            logger.error(f"Validation failed for '{tool.get('name', 'unknown')}': {self.errors}")
            return None
        if self.warnings:
            logger.warning(f"Validation warnings for '{tool['name']}': {self.warnings}")
        
        return tool
    
    def _validate_pricing(self, pricing: dict) -> dict:
        """Validate and normalize pricing section."""
        result = {
            'has_free_tier': bool(pricing.get('has_free_tier', False)),
            'free_details': str(pricing.get('free_details', '')).strip() or None,
            'paid_starts_at': str(pricing.get('paid_starts_at', '')).strip() or None,
            'pricing_url': None,
        }
        
        # Validate pricing URL
        pricing_url = pricing.get('pricing_url', '')
        if pricing_url and is_valid_url(pricing_url):
            result['pricing_url'] = pricing_url
        
        return result
    
    def _validate_api(self, api: dict) -> dict:
        """Validate and normalize API section."""
        result = {
            'available': bool(api.get('available', False)),
            'docs_url': None,
            'key_url': None,
            'base_url': None,
            'rate_limits': str(api.get('rate_limits', '')).strip() or None,
            'env_var_name': str(api.get('env_var_name', '')).strip() or None,
            'auth_method': None,
        }
        
        # Validate URLs
        for url_field in ['docs_url', 'key_url', 'base_url']:
            url = api.get(url_field, '')
            if url and is_valid_url(url):
                result[url_field] = url
        
        # Validate auth method
        auth = api.get('auth_method', '')
        if auth in VALID_AUTH_METHODS:
            result['auth_method'] = auth
        
        return result
    
    def validate_batch(self, tools: list[dict]) -> list[dict]:
        """
        Validate a batch of tools, returning only valid ones.
        
        Also logs summary statistics.
        """
        valid_tools = []
        failed_count = 0
        
        for tool in tools:
            validated = self.validate(tool)
            if validated:
                valid_tools.append(validated)
            else:
                failed_count += 1
        
        logger.info(f"Validation complete: {len(valid_tools)} valid, {failed_count} failed")
        return valid_tools
