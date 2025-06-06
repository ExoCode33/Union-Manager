import asyncpg
import os

async def get_connection():
    return await asyncpg.connect(
        host=os.getenv("PGHOST"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        database=os.getenv("PGDATABASE"),
        port=int(os.getenv("PGPORT", 5432))
    )
