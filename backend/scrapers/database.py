"""
Database Layer
==============
SQLite-based storage for AI tools with easy PostgreSQL migration path.

WHY DATABASE INSTEAD OF JSON:
1. Better performance with 10,000+ tools
2. Easy querying (filter by category, search by name)
3. Atomic updates (no race conditions)
4. Change tracking (when was tool last updated?)
5. Relationships (tools <-> categories, tools <-> tags)

SCHEMA DESIGN:
- tools: Main tool data
- tool_categories: Many-to-many relationship
- tool_tags: Many-to-many relationship  
- scrape_history: Track when tools were scraped/updated

USAGE:
    from scrapers.database import Database
    
    db = Database()  # Uses SQLite by default
    
    # Add/update tools
    db.upsert_tool(tool_dict)
    db.upsert_tools(list_of_tools)
    
    # Query tools
    tools = db.get_all_tools()
    tools = db.search_tools("chatgpt")
    tools = db.get_tools_by_category("llm")
"""

import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Database:
    """
    SQLite database for AI tools storage.
    
    Designed to be easily swapped for PostgreSQL later.
    All SQL is standard and compatible with both.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file. 
                    Defaults to backend/data/tools.db
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "tools.db"
        
        self.db_path = str(db_path)
        self._init_db()
    
    def _init_db(self):
        """Create tables if they don't exist."""
        with self._get_connection() as conn:
            conn.executescript("""
                -- Main tools table
                CREATE TABLE IF NOT EXISTS tools (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    tagline TEXT,
                    website TEXT NOT NULL,
                    logo_url TEXT,
                    status TEXT DEFAULT 'active',
                    
                    -- Pricing (stored as JSON for flexibility)
                    pricing_json TEXT,
                    
                    -- API info (stored as JSON)
                    api_json TEXT,
                    
                    -- Free alternatives (stored as JSON array)
                    free_alternatives_json TEXT,
                    
                    -- Metadata
                    free_tier_verified_date TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    source TEXT  -- Where we scraped this from
                );
                
                -- Categories (fixed list)
                CREATE TABLE IF NOT EXISTS categories (
                    id TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    description TEXT,
                    color TEXT
                );
                
                -- Tool-Category relationship (many-to-many)
                CREATE TABLE IF NOT EXISTS tool_categories (
                    tool_id TEXT NOT NULL,
                    category_id TEXT NOT NULL,
                    PRIMARY KEY (tool_id, category_id),
                    FOREIGN KEY (tool_id) REFERENCES tools(id) ON DELETE CASCADE,
                    FOREIGN KEY (category_id) REFERENCES categories(id)
                );
                
                -- Tags (freeform)
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                );
                
                -- Tool-Tag relationship
                CREATE TABLE IF NOT EXISTS tool_tags (
                    tool_id TEXT NOT NULL,
                    tag_id INTEGER NOT NULL,
                    PRIMARY KEY (tool_id, tag_id),
                    FOREIGN KEY (tool_id) REFERENCES tools(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags(id)
                );
                
                -- Scrape history (for tracking updates)
                CREATE TABLE IF NOT EXISTS scrape_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    tools_found INTEGER DEFAULT 0,
                    tools_added INTEGER DEFAULT 0,
                    tools_updated INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'running',
                    error_message TEXT
                );
                
                -- Indexes for common queries
                CREATE INDEX IF NOT EXISTS idx_tools_name ON tools(name);
                CREATE INDEX IF NOT EXISTS idx_tools_status ON tools(status);
                CREATE INDEX IF NOT EXISTS idx_tools_updated ON tools(updated_at);
                CREATE INDEX IF NOT EXISTS idx_tool_categories_category ON tool_categories(category_id);
                CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
            """)
            
            # Insert default categories
            categories = [
                ('llm', 'LLM & Chat', 'Large language models and conversational AI', 'purple'),
                ('code', 'Code & Dev', 'AI coding assistants and developer tools', 'blue'),
                ('image', 'Image Generation', 'AI image and art generation tools', 'pink'),
                ('video', 'Video', 'AI video generation and editing', 'coral'),
                ('audio', 'Audio & Music', 'AI music, sound, and voice generation', 'amber'),
                ('search', 'Search & Research', 'AI-powered search and research tools', 'teal'),
                ('agents', 'Agents & Automation', 'AI agents, workflows, and automation', 'green'),
                ('embeddings', 'Embeddings & RAG', 'Vector embeddings and retrieval pipelines', 'blue'),
                ('speech', 'Speech & Voice', 'Speech-to-text, text-to-speech, and voice cloning', 'teal'),
                ('productivity', 'Productivity', 'AI tools for writing, notes, and workflows', 'gray'),
            ]
            
            conn.executemany("""
                INSERT OR IGNORE INTO categories (id, label, description, color)
                VALUES (?, ?, ?, ?)
            """, categories)
            
            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with automatic cleanup."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Access columns by name
        try:
            yield conn
        finally:
            conn.close()
    
    def upsert_tool(self, tool: dict, source: str = "manual") -> bool:
        """
        Insert or update a tool.
        
        Args:
            tool: Tool dictionary matching our schema
            source: Where this data came from (futurepedia, taaft, etc.)
        
        Returns:
            True if inserted (new), False if updated (existing)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if tool exists
            cursor.execute("SELECT id FROM tools WHERE id = ?", (tool['id'],))
            exists = cursor.fetchone() is not None
            
            # Prepare JSON fields
            pricing_json = json.dumps(tool.get('pricing', {}))
            api_json = json.dumps(tool.get('api', {}))
            free_alts_json = json.dumps(tool.get('free_alternatives', []))
            
            if exists:
                # Update existing tool
                cursor.execute("""
                    UPDATE tools SET
                        name = ?,
                        tagline = ?,
                        website = ?,
                        logo_url = ?,
                        status = ?,
                        pricing_json = ?,
                        api_json = ?,
                        free_alternatives_json = ?,
                        free_tier_verified_date = ?,
                        updated_at = CURRENT_TIMESTAMP,
                        source = COALESCE(source, ?)
                    WHERE id = ?
                """, (
                    tool['name'],
                    tool.get('tagline'),
                    tool['website'],
                    tool.get('logo_url'),
                    tool.get('status', 'active'),
                    pricing_json,
                    api_json,
                    free_alts_json,
                    tool.get('free_tier_verified_date'),
                    source,
                    tool['id']
                ))
            else:
                # Insert new tool
                cursor.execute("""
                    INSERT INTO tools (
                        id, name, tagline, website, logo_url, status,
                        pricing_json, api_json, free_alternatives_json,
                        free_tier_verified_date, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tool['id'],
                    tool['name'],
                    tool.get('tagline'),
                    tool['website'],
                    tool.get('logo_url'),
                    tool.get('status', 'active'),
                    pricing_json,
                    api_json,
                    free_alts_json,
                    tool.get('free_tier_verified_date'),
                    source
                ))
            
            # Handle categories
            cursor.execute("DELETE FROM tool_categories WHERE tool_id = ?", (tool['id'],))
            for cat_id in tool.get('categories', []):
                cursor.execute("""
                    INSERT OR IGNORE INTO tool_categories (tool_id, category_id)
                    VALUES (?, ?)
                """, (tool['id'], cat_id))
            
            # Handle tags
            cursor.execute("DELETE FROM tool_tags WHERE tool_id = ?", (tool['id'],))
            for tag_name in tool.get('tags', []):
                # Insert tag if not exists
                cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,))
                cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
                tag_id = cursor.fetchone()[0]
                cursor.execute("""
                    INSERT OR IGNORE INTO tool_tags (tool_id, tag_id)
                    VALUES (?, ?)
                """, (tool['id'], tag_id))
            
            conn.commit()
            return not exists
    
    def upsert_tools(self, tools: list[dict], source: str = "manual") -> dict:
        """
        Insert or update multiple tools.
        
        Returns:
            Dict with counts: {added: N, updated: M}
        """
        added = 0
        updated = 0
        
        for tool in tools:
            if self.upsert_tool(tool, source):
                added += 1
            else:
                updated += 1
        
        logger.info(f"Upserted {len(tools)} tools: {added} added, {updated} updated")
        return {'added': added, 'updated': updated}
    
    def get_tool(self, tool_id: str) -> Optional[dict]:
        """Get a single tool by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tools WHERE id = ?", (tool_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return self._row_to_tool(conn, row)
    
    def get_all_tools(self, limit: int = None, offset: int = 0) -> list[dict]:
        """Get all tools with optional pagination."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM tools ORDER BY name"
            if limit:
                query += f" LIMIT {limit} OFFSET {offset}"
            
            cursor.execute(query)
            return [self._row_to_tool(conn, row) for row in cursor.fetchall()]
    
    def search_tools(self, query: str, limit: int = 50) -> list[dict]:
        """
        Search tools by name or tagline.
        
        Uses SQLite LIKE for simplicity. For production,
        consider full-text search (FTS5) or external search.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tools 
                WHERE name LIKE ? OR tagline LIKE ?
                ORDER BY name
                LIMIT ?
            """, (f'%{query}%', f'%{query}%', limit))
            
            return [self._row_to_tool(conn, row) for row in cursor.fetchall()]
    
    def get_tools_by_category(self, category_id: str) -> list[dict]:
        """Get all tools in a category."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.* FROM tools t
                JOIN tool_categories tc ON t.id = tc.tool_id
                WHERE tc.category_id = ?
                ORDER BY t.name
            """, (category_id,))
            
            return [self._row_to_tool(conn, row) for row in cursor.fetchall()]
    
    def get_tools_with_free_tier(self) -> list[dict]:
        """Get all tools that have a free tier."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tools 
                WHERE json_extract(pricing_json, '$.has_free_tier') = 1
                ORDER BY name
            """)
            
            return [self._row_to_tool(conn, row) for row in cursor.fetchall()]
    
    def get_tools_with_api(self) -> list[dict]:
        """Get all tools that have an API."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tools 
                WHERE json_extract(api_json, '$.available') = 1
                ORDER BY name
            """)
            
            return [self._row_to_tool(conn, row) for row in cursor.fetchall()]
    
    def get_recently_updated(self, days: int = 7, limit: int = 50) -> list[dict]:
        """Get tools updated in the last N days."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tools 
                WHERE updated_at >= datetime('now', ?)
                ORDER BY updated_at DESC
                LIMIT ?
            """, (f'-{days} days', limit))
            
            return [self._row_to_tool(conn, row) for row in cursor.fetchall()]
    
    def _row_to_tool(self, conn, row: sqlite3.Row) -> dict:
        """Convert database row to tool dictionary."""
        cursor = conn.cursor()
        tool_id = row['id']
        
        # Get categories
        cursor.execute("""
            SELECT category_id FROM tool_categories WHERE tool_id = ?
        """, (tool_id,))
        categories = [r[0] for r in cursor.fetchall()]
        
        # Get tags
        cursor.execute("""
            SELECT t.name FROM tags t
            JOIN tool_tags tt ON t.id = tt.tag_id
            WHERE tt.tool_id = ?
        """, (tool_id,))
        tags = [r[0] for r in cursor.fetchall()]
        
        return {
            'id': row['id'],
            'name': row['name'],
            'tagline': row['tagline'],
            'website': row['website'],
            'logo_url': row['logo_url'],
            'categories': categories,
            'tags': tags,
            'pricing': json.loads(row['pricing_json'] or '{}'),
            'api': json.loads(row['api_json'] or '{}'),
            'free_alternatives': json.loads(row['free_alternatives_json'] or '[]'),
            'status': row['status'],
            'free_tier_verified_date': row['free_tier_verified_date'],
        }
    
    def get_stats(self) -> dict:
        """Get database statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Total tools
            cursor.execute("SELECT COUNT(*) FROM tools")
            stats['total_tools'] = cursor.fetchone()[0]
            
            # Tools by category
            cursor.execute("""
                SELECT c.id, c.label, COUNT(tc.tool_id) as count
                FROM categories c
                LEFT JOIN tool_categories tc ON c.id = tc.category_id
                GROUP BY c.id
                ORDER BY count DESC
            """)
            stats['by_category'] = {row[0]: {'label': row[1], 'count': row[2]} 
                                    for row in cursor.fetchall()}
            
            # Tools with free tier
            cursor.execute("""
                SELECT COUNT(*) FROM tools 
                WHERE json_extract(pricing_json, '$.has_free_tier') = 1
            """)
            stats['with_free_tier'] = cursor.fetchone()[0]
            
            # Tools with API
            cursor.execute("""
                SELECT COUNT(*) FROM tools 
                WHERE json_extract(api_json, '$.available') = 1
            """)
            stats['with_api'] = cursor.fetchone()[0]
            
            return stats
    
    def log_scrape(self, source: str) -> int:
        """Start logging a scrape run. Returns the run ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO scrape_history (source, started_at)
                VALUES (?, datetime('now'))
            """, (source,))
            conn.commit()
            return cursor.lastrowid
    
    def complete_scrape(self, run_id: int, found: int, added: int, updated: int):
        """Mark a scrape run as complete."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE scrape_history SET
                    completed_at = datetime('now'),
                    tools_found = ?,
                    tools_added = ?,
                    tools_updated = ?,
                    status = 'completed'
                WHERE id = ?
            """, (found, added, updated, run_id))
            conn.commit()
    
    def export_to_json(self, path: str = None) -> str:
        """Export all tools to JSON file."""
        tools = self.get_all_tools()
        
        if path is None:
            path = Path(self.db_path).parent / "tools_export.json"
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(tools, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported {len(tools)} tools to {path}")
        return str(path)
    
    def import_from_json(self, path: str, source: str = "import") -> dict:
        """Import tools from JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            tools = json.load(f)
        
        return self.upsert_tools(tools, source)
