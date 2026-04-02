from fastapi import APIRouter, Query
from typing import List
from models import Tool
from data_loader import get_tools

router = APIRouter()


def simple_search(tools: List[Tool], query: str) -> List[Tool]:
    q = query.lower().strip()
    results = []
    for tool in tools:
        score = 0
        if q in tool.name.lower():
            score += 10
        if q in tool.tagline.lower():
            score += 5
        for cat in tool.categories:
            if q in cat.lower():
                score += 4
        for tag in tool.tags:
            if q in tag.lower():
                score += 3
        if score > 0:
            results.append((tool, score))
    results.sort(key=lambda x: x[1], reverse=True)
    return [tool for tool, _ in results]


@router.get("/", response_model=List[Tool])
def search_tools(q: str = Query(..., min_length=1, description="Search query")):
    tools = get_tools()
    return simple_search(tools, q)