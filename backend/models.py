from pydantic import BaseModel
from typing import Optional, List


class Pricing(BaseModel):
    has_free_tier: bool
    free_details: str
    paid_starts_at: str
    pricing_url: str


class ApiInfo(BaseModel):
    available: bool
    docs_url: Optional[str] = ""
    key_url: Optional[str] = ""
    base_url: Optional[str] = ""
    rate_limits: Optional[str] = ""
    env_var_name: Optional[str] = ""
    auth_method: Optional[str] = ""


class Tool(BaseModel):
    id: str
    name: str
    tagline: str
    website: str
    logo_url: str
    categories: List[str]
    tags: List[str]
    pricing: Pricing
    api: ApiInfo
    free_alternatives: List[str]
    status: str
    free_tier_verified_date: str


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