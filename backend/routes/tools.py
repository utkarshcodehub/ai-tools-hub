from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from models import Tool
from data_loader import get_tools, get_tool_by_id, get_alternatives

router = APIRouter()


@router.get("/", response_model=List[Tool])
def list_tools(
    category: Optional[str] = Query(None, description="Filter by category id"),
    has_free_tier: Optional[bool] = Query(None, description="Filter by free tier"),
    has_api: Optional[bool] = Query(None, description="Filter by API availability"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    tools = get_tools()

    if category:
        tools = [t for t in tools if category in t.categories]
    if has_free_tier is not None:
        tools = [t for t in tools if t.pricing.has_free_tier == has_free_tier]
    if has_api is not None:
        tools = [t for t in tools if t.api.available == has_api]
    if tag:
        tools = [t for t in tools if tag in t.tags]
    if status:
        tools = [t for t in tools if t.status == status]

    return tools


@router.get("/trending", response_model=List[Tool])
def get_trending():
    tools = get_tools()
    trending = [t for t in tools if "trending" in t.tags]
    return trending[:8]


@router.get("/free", response_model=List[Tool])
def get_free_tools():
    tools = get_tools()
    return [t for t in tools if t.pricing.has_free_tier]


@router.get("/compare", response_model=List[Tool])
def compare_tools(ids: str = Query(..., description="Comma-separated tool IDs")):
    tool_ids = [i.strip() for i in ids.split(",")]
    results = []
    for tid in tool_ids:
        tool = get_tool_by_id(tid)
        if tool:
            results.append(tool)
    if not results:
        raise HTTPException(status_code=404, detail="No tools found for given IDs")
    return results


@router.get("/env-template")
def get_env_template(ids: str = Query(..., description="Comma-separated tool IDs")):
    tool_ids = [i.strip() for i in ids.split(",")]
    lines = ["# AI Tools Hub — .env template", "# Generated for your selected tools", ""]
    found_any = False
    for tid in tool_ids:
        tool = get_tool_by_id(tid)
        if tool and tool.api.available and tool.api.env_var_name:
            lines.append(f"# {tool.name}")
            lines.append(f"# Docs: {tool.api.docs_url}")
            lines.append(f"# Get key: {tool.api.key_url}")
            lines.append(f"{tool.api.env_var_name}=your_key_here")
            lines.append("")
            found_any = True
    if not found_any:
        return {"template": "# No API keys needed for the selected tools"}
    return {"template": "\n".join(lines)}


@router.get("/alternatives/{tool_id}", response_model=List[Tool])
def get_free_alternatives(tool_id: str):
    tool = get_tool_by_id(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_id}' not found")
    alt_ids = tool.free_alternatives
    results = []
    for aid in alt_ids:
        alt = get_tool_by_id(aid)
        if alt:
            results.append(alt)
    return results


@router.get("/{tool_id}", response_model=Tool)
def get_tool(tool_id: str):
    tool = get_tool_by_id(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_id}' not found")
    return tool