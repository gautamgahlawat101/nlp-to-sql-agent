"""
SQLAlchemy engine for the agent's DB connection.
IMPORTANT: the DB_USER in .env must be a read-only role — see
db/schema_setup/README notes on granting SELECT-only privileges.
This module only ever opens connections; it never issues DDL/DML.
"""
from sqlalchemy import create_engine, text
from config.settings import DATABASE_URL, QUERY_TIMEOUT_SECONDS

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            connect_args={"options": f"-c statement_timeout={QUERY_TIMEOUT_SECONDS * 1000}"},
        )
    return _engine


def run_query(sql: str):
    """Execute a validated, read-only SQL string and return rows as dicts."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        columns = result.keys()
        return [dict(zip(columns, row)) for row in result.fetchall()]
