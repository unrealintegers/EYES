import os

import psycopg
import psycopg.rows
from psycopg_pool import AsyncConnectionPool

class DatabaseManager:
    def __init__(self):
        self.pool = None

    async def init(self):
        async def configure(conn):
            await conn.set_autocommit(True)

        self.pool = AsyncConnectionPool(os.getenv("DB_CREDS"), configure=configure)

    async def copy_to(self, query, rows):
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                async with cur.copy(query) as copy:
                    for row in rows:
                        await copy.write_row(row)

    async def run(self, query, vars=tuple()):
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, vars)

    async def run_batch(self, query, vars=tuple()):
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.executemany(query, vars)

    async def fetch_tup(self, query, vars=tuple()):
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, vars)

                return await cur.fetchall()

    async def fetch_dict(self, query, vars=tuple()):
        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(query, vars)

                return await cur.fetchall()
