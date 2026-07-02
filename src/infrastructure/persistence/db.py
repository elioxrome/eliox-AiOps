from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


def create_pool(database_url: str) -> ConnectionPool:
    pool = ConnectionPool(
        database_url,
        min_size=1,
        max_size=10,
        open=False,
        kwargs={"row_factory": dict_row},
        configure=register_vector,
    )
    pool.open(wait=True)
    return pool
