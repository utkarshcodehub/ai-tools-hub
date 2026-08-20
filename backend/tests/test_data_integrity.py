import json
from pathlib import Path

from pydantic import ValidationError

from models import Tool

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _load_json(name):
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def test_tools_json_matches_schema():
    raw = _load_json("tools.json")
    errors = []
    for item in raw:
        try:
            Tool(**item)
        except ValidationError as e:
            errors.append(f"{item.get('id', '?')}: {e}")
    assert not errors, "Invalid tool records:\n" + "\n".join(errors)


def test_no_dangling_category_references():
    tools = _load_json("tools.json")
    categories = _load_json("categories.json")
    valid_category_ids = {c["id"] for c in categories}

    bad = {
        (t["id"], c)
        for t in tools
        for c in t.get("categories", [])
        if c not in valid_category_ids
    }
    assert not bad, f"Tools referencing unknown categories: {bad}"


def test_no_dangling_free_alternative_references():
    tools = _load_json("tools.json")
    tool_ids = {t["id"] for t in tools}

    bad = {
        (t["id"], a)
        for t in tools
        for a in t.get("free_alternatives", [])
        if a not in tool_ids
    }
    assert not bad, f"Tools referencing missing free_alternatives: {bad}"


def test_no_duplicate_tool_ids():
    tools = _load_json("tools.json")
    ids = [t["id"] for t in tools]
    dupes = {i for i in ids if ids.count(i) > 1}
    assert not dupes, f"Duplicate tool ids: {dupes}"


def test_no_sentence_like_names():
    """
    Regression guard for the Hacker News scraper bug where full sentences
    ("I trained a 125M model to autocomplete piano on") were mistaken for
    product names instead of the actual tool name.
    """
    tools = _load_json("tools.json")
    suspicious = [t["id"] for t in tools if len(t["name"].split()) > 8]
    assert not suspicious, f"Sentence-like tool names found: {suspicious}"
