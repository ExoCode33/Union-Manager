import asyncpg
import os
from urllib.parse import urlparse

async def get_connection():
    """Get a PostgreSQL connection using asyncpg"""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable not set")

    result = urlparse(database_url)

    return await asyncpg.connect(
        user=result.username,
        password=result.password,
        database=result.path[1:],
        host=result.hostname,
        port=result.port,
        ssl='require'
    )
