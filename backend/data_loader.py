import json
import os
from pathlib import Path
from typing import List, Dict
from models import Tool, Category

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def load_tools() -> List[Tool]:
    with open(DATA_DIR / "tools.json", "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Tool(**item) for item in raw]


def load_categories() -> List[Category]:
    with open(DATA_DIR / "categories.json", "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Category(**item) for item in raw]


def load_free_alternatives() -> Dict:
    with open(DATA_DIR / "free_alternatives.json", "r", encoding="utf-8") as f:
        return json.load(f)


tools_db: List[Tool] = load_tools()
categories_db: List[Category] = load_categories()
alternatives_db: Dict = load_free_alternatives()


def get_tools() -> List[Tool]:
    return tools_db


def get_tool_by_id(tool_id: str) -> Tool | None:
    return next((t for t in tools_db if t.id == tool_id), None)


def get_categories() -> List[Category]:
    return categories_db


def get_alternatives() -> Dict:
    return alternatives_db