import os

import psycopg
import psycopg.rows


class DatabaseManager:
    def __init__(self):
        self.conn = None

    async def init(self):
        self.conn = await psycopg.AsyncConnection.connect(os.getenv("DB_CREDS"), autocommit=True)

    # Implement some behaviour of the connection class
    async def __aenter__(self):
        return self.conn.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self.conn.__exit__(exc_type, exc_val, exc_tb)

    def __getattr__(self, item):
        return getattr(self.conn, item)

    async def run(self, query, vars=tuple()):
        async with self.conn.cursor() as cur:
            await cur.execute(query, vars)

    async def run_batch(self, query, vars=tuple()):
        async with self.conn.cursor() as cur:
            await cur.executemany(query, vars)

    async def fetch_tup(self, query, vars=tuple()):
        async with self.conn.cursor() as cur:
            await cur.execute(query, vars)

            return await cur.fetchall()

    async def fetch_dict(self, query, vars=tuple()):
        async with self.conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(query, vars)

            return await cur.fetchall()
