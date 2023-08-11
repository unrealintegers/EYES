import os

import psycopg2
import psycopg2.extras


class DatabaseManager:
    def __init__(self):
        self.conn = psycopg2.connect(os.getenv("DB_CREDS"))

    # Implement some behaviour of the connection class
    def __enter__(self):
        return self.conn.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.conn.__exit__(exc_type, exc_val, exc_tb)

    def __getattr__(self, item):
        return getattr(self.conn, item)

    def run(self, query, vars=tuple()):
        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute(query, vars)

    def run_batch(self, query, vars=tuple()):
        with self.conn:
            with self.conn.cursor() as cur:
                psycopg2.extras.execute_batch(cur, query, vars)

    def fetch_tup(self, query, vars=tuple()):
        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute(query, vars)

                return cur.fetchall()

    def fetch_dict(self, query, vars=tuple()):
        with self.conn:
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, vars)

                return cur.fetchall()
