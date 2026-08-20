from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy"}


def test_list_tools():
    r = client.get("/tools/")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_get_tool_by_id():
    tools = client.get("/tools/").json()
    first_id = tools[0]["id"]
    r = client.get(f"/tools/{first_id}")
    assert r.status_code == 200
    assert r.json()["id"] == first_id


def test_get_tool_not_found():
    r = client.get("/tools/does-not-exist")
    assert r.status_code == 404


def test_categories():
    r = client.get("/categories/")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) > 0


def test_search():
    r = client.get("/search/", params={"q": "AI"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_free_alternatives_resolve_fully():
    """
    Regression guard for dangling free_alternatives references: every id
    listed on a tool should resolve to a real tool via the API.
    """
    tools = client.get("/tools/").json()
    with_alts = [t for t in tools if t["free_alternatives"]]
    assert with_alts, "expected at least one tool with free_alternatives"

    tool = with_alts[0]
    r = client.get(f"/tools/alternatives/{tool['id']}")
    assert r.status_code == 200
    assert len(r.json()) == len(tool["free_alternatives"])
