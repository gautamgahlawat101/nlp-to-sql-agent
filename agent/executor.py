"""
agent/executor.py

The "courier": runs validated, read-only SQL against the real database using
a dedicated, permission-restricted role (never the admin/owner role used for
schema setup and seeding), and returns results as a list of dicts.
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine, text
from config.settings import AGENT_DATABASE_URL, QUERY_TIMEOUT_SECONDS, MAX_ROW_LIMIT

_engine = None


def get_agent_engine():
    """
    Deliberately separate from db/connection.py's get_engine() — that one
    uses the full-privilege owner role for schema setup and seeding. This one
    uses the restricted read-only role, since this is the connection the
    LLM-generated SQL actually runs through.
    """
    global _engine
    if _engine is None:
        _engine = create_engine(
            AGENT_DATABASE_URL,
            pool_pre_ping=True,
            connect_args={
                "options": f"-c statement_timeout={QUERY_TIMEOUT_SECONDS * 1000}",
                "connect_timeout": 10,
            },
        )
    return _engine


def execute_query(sql: str) -> list[dict]:
    """
    Executes already-validated SQL and returns rows as a list of dicts.
    Assumes sql_validator.validate_sql() has already approved this string —
    this function only executes, and enforces MAX_ROW_LIMIT as a final
    safety net regardless of what LIMIT (if any) the query itself has.
    """
    engine = get_agent_engine()
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        columns = result.keys()
        rows = result.fetchmany(MAX_ROW_LIMIT)
        return [dict(zip(columns, row)) for row in rows]


if __name__ == "__main__":
    from agent.sql_validator import validate_sql

    test_sql = "SELECT customer_id, city, state FROM customer.customers LIMIT 5;"
    print(f"Testing: {test_sql}\n")

    validated = validate_sql(test_sql)
    rows = execute_query(validated)

    print(f"Retrieved {len(rows)} rows:")
    for row in rows:
        print(f"  {row}")