"""
agent/sql_validator.py

The "security guard": inspects LLM-generated SQL before it's ever allowed to
run against the real database. Rejects anything that isn't a single,
read-only SELECT statement, rejects write operations hidden inside a WITH
clause (Postgres allows data-modifying CTEs), and rejects any table
reference that doesn't actually exist in your schema — catching hallucinated
names before they cause a confusing database error.
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import sqlglot
from sqlglot import exp
import pandas as pd

from config.settings import METADATA_CSV_PATH


class ValidationError(Exception):
    """Raised when generated SQL fails a safety or correctness check."""
    pass


def _load_known_tables():
    df = pd.read_csv(METADATA_CSV_PATH)
    return set((df["schema_name"] + "." + df["table_name"]).str.lower())


_KNOWN_TABLES = _load_known_tables()


def extract_sql(raw_response: str) -> str:
    """
    LLMs sometimes wrap SQL in markdown code fences even when told not to.
    Strip those off before parsing rather than failing validation on
    formatting alone.
    """
    text = raw_response.strip()
    if text.startswith("```"):
        lines = [l for l in text.split("\n") if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return text


def validate_sql(raw_response: str) -> str:
    """
    Validates a raw LLM response as safe, single-statement, schema-consistent
    SQL. Returns the cleaned SQL string if every check passes, or raises
    ValidationError with a specific, actionable reason if it doesn't.
    """
    sql = extract_sql(raw_response)

    try:
        statements = [s for s in sqlglot.parse(sql, read="postgres") if s is not None]
    except Exception as e:
        raise ValidationError(f"Could not parse SQL: {e}")

    if len(statements) == 0:
        raise ValidationError("No valid SQL statement found.")
    if len(statements) > 1:
        raise ValidationError(
            f"Expected exactly one statement, found {len(statements)} — "
            "possible stacked/chained statements."
        )

    stmt = statements[0]

    if not isinstance(stmt, exp.Select):
        raise ValidationError(
            f"Only SELECT statements are allowed — got {type(stmt).__name__}."
        )

    # Defense in depth: Postgres allows data-modifying CTEs (WITH x AS
    # (DELETE FROM ... RETURNING *) SELECT * FROM x) — a write operation
    # disguised inside what looks like a top-level SELECT. Check explicitly.
    for forbidden_type in (exp.Insert, exp.Update, exp.Delete):
        if list(stmt.find_all(forbidden_type)):
            raise ValidationError(
                f"Forbidden operation detected inside statement: "
                f"{forbidden_type.__name__} (possibly hidden inside a WITH clause)."
            )

    # CTE names are local aliases, not real tables — exclude them from the
    # "must be a real, schema-qualified table" check below.
    cte_names = {cte.alias_or_name.lower() for cte in stmt.find_all(exp.CTE)}

    for table in stmt.find_all(exp.Table):
        name = table.name.lower()
        if name in cte_names:
            continue
        schema = table.db.lower() if table.db else ""
        if not schema:
            raise ValidationError(
                f"Table '{name}' is not schema-qualified (e.g. should be "
                f"'customer.{name}') — every real table reference must include its schema."
            )
        full_name = f"{schema}.{name}"
        if full_name not in _KNOWN_TABLES:
            raise ValidationError(
                f"Unknown table referenced: {full_name} — not found in schema_metadata.csv."
            )

    return stmt.sql(dialect="postgres")


if __name__ == "__main__":
    test_cases = [
        ("SELECT customer_id FROM customer.customers LIMIT 10;", True),
        ("DELETE FROM customer.customers;", False),
        ("SELECT * FROM customer.customers; DROP TABLE customer.customers;", False),
        ("SELECT * FROM fake_schema.fake_table;", False),
        ("SELECT customer_id FROM customers LIMIT 10;", False),
        ("WITH x AS (DELETE FROM customer.customers RETURNING *) SELECT * FROM x;", False),
    ]

    for sql, should_pass in test_cases:
        print(f"\nTesting: {sql}")
        try:
            result = validate_sql(sql)
            status = "PASSED" if should_pass else "UNEXPECTEDLY PASSED (bug!)"
            print(f"  {status}: {result}")
        except ValidationError as e:
            status = "REJECTED (expected)" if not should_pass else "UNEXPECTEDLY REJECTED (bug!)"
            print(f"  {status}: {e}")
            