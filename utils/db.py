import sqlite3
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_connection():
    """Async context manager for SQLite connections"""
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row  # This allows dict-like access to rows
    try:
        yield conn
    finally:
        conn.close()

# Alternative simpler function if you prefer
def get_sync_connection():
    """Get synchronous SQLite connection"""
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn
