from pydantic import BaseModel
from typing import Optional, List


class Pricing(BaseModel):
    has_free_tier: bool = False
    free_details: Optional[str] = None
    paid_starts_at: Optional[str] = None
    pricing_url: Optional[str] = None


class ApiInfo(BaseModel):
    available: bool = False
    docs_url: Optional[str] = None
    key_url: Optional[str] = None
    base_url: Optional[str] = None
    rate_limits: Optional[str] = None
    env_var_name: Optional[str] = None
    auth_method: Optional[str] = None


class Tool(BaseModel):
    id: str
    name: str
    tagline: str
    website: str
    logo_url: Optional[str] = None
    categories: List[str] = []
    tags: List[str] = []
    pricing: Pricing = Pricing()
    api: ApiInfo = ApiInfo()
    free_alternatives: List[str] = []
    status: str = "active"
    free_tier_verified_date: Optional[str] = None


class Category(BaseModel):
    id: str
    label: str
    description: str
    color: str


class SearchResult(BaseModel):
    tool: Tool
    score: float


class EnvTemplate(BaseModel):
    tool_ids: List[str]