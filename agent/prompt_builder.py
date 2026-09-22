"""
agent/prompt_builder.py

The "translator" (prompt half): assembles the system + user messages sent to
the LLM, combining the retrieved schema slice from metadata_retriever.py with
dialect rules, safety constraints, and a few worked examples from
data/few_shot_examples.json.
"""
import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.settings import FEW_SHOT_EXAMPLES_PATH, MAX_ROW_LIMIT

SYSTEM_PROMPT_TEMPLATE = """You are a SQL generation assistant for a PostgreSQL database.

DIALECT AND NAMING RULES:
- This is PostgreSQL, not MySQL or SQL Server — use PostgreSQL syntax only.
- The database has 6 separate schemas: campaign, customer, products, sales, loyalty, market_data.
- ALWAYS fully qualify every table with its schema, e.g. sales.orders, not just orders.
- Only use tables and columns explicitly listed below in AVAILABLE SCHEMA — never invent a column or table name.

SAFETY RULES:
- Generate exactly one SELECT statement. Never generate INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, or GRANT.
- Never generate multiple statements separated by semicolons.
- Always include a LIMIT clause of at most {max_rows} rows, unless the question explicitly asks for an aggregate (e.g. COUNT, SUM, AVG) that returns a single row.
- The market_data schema tracks exactly one company (this business itself). Never ask which company — market_data.companies always has one row, just use it.
- Unless the question specifies otherwise, "revenue" means the sum of sales.transactions.transaction_amount.

CLARIFICATION RULE:
- If the question is genuinely ambiguous (e.g. "top customers" without specifying by what measure, or an unclear grouping/dimension), do not guess. Instead, respond with exactly: CLARIFY: <a specific question that would resolve the ambiguity>
- Do NOT ask for clarification about the current date or "today". For relative time references like "this year", "last quarter", "recently", or "today", use PostgreSQL's CURRENT_DATE or CURRENT_TIMESTAMP directly in the SQL — the database resolves these correctly at query time, so you never need to know or guess what today's date actually is.
- Only use CLARIFY when truly necessary — most questions should be answered directly with SQL.

OUTPUT FORMAT:
- Respond with ONLY the SQL query. No explanation, no markdown code fences, no commentary.

AVAILABLE SCHEMA (only the columns relevant to this question):
{schema_slice}

{few_shot_examples}
"""


def _format_schema_slice(columns: list[dict]) -> str:
    """
    Groups the retrieved column rows by table and renders them as a compact,
    LLM-readable block — this is what actually goes into the prompt, not the
    raw CSV rows.
    """
    tables = {}
    for col in columns:
        key = f"{col['schema_name']}.{col['table_name']}"
        tables.setdefault(key, []).append(col)

    lines = []
    for table_name, cols in tables.items():
        lines.append(f"Table: {table_name}")
        for c in cols:
            flags = []
            if c.get("is_primary_key") == "Y":
                flags.append("PRIMARY KEY")
            if c.get("is_foreign_key") == "Y":
                flags.append(f"FOREIGN KEY -> {c.get('references')}")
            flag_str = f" [{', '.join(flags)}]" if flags else ""
            lines.append(
                f"  - {c['column_name']} ({c['data_type']}){flag_str}: {c['description']}"
            )
        lines.append("")
    return "\n".join(lines)


def _load_few_shot_examples() -> str:
    if not os.path.exists(FEW_SHOT_EXAMPLES_PATH):
        return ""
    with open(FEW_SHOT_EXAMPLES_PATH) as f:
        examples = json.load(f)

    lines = ["EXAMPLES:"]
    for ex in examples:
        lines.append(f"Q: {ex['question']}")
        lines.append(f"A: {ex['sql']}")
        lines.append("")
    return "\n".join(lines)


def build_prompt(question: str, retrieved_columns: list[dict]) -> tuple[str, str]:
    """Returns (system_prompt, user_prompt) ready to send to llm_client.generate_sql()."""
    schema_slice = _format_schema_slice(retrieved_columns)
    few_shot = _load_few_shot_examples()

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        max_rows=MAX_ROW_LIMIT,
        schema_slice=schema_slice,
        few_shot_examples=few_shot,
    )
    user_prompt = f"Question: {question}"

    return system_prompt, user_prompt


if __name__ == "__main__":
    from agent.metadata_retriever import retrieve_relevant_columns
    from agent.llm_client import generate_sql

    q = " ".join(sys.argv[1:]) or "top customers by revenue this year"
    cols = retrieve_relevant_columns(q)
    system_prompt, user_prompt = build_prompt(q, cols)

    print(f"Question: {q}")
    print(f"Retrieved {len(cols)} relevant columns for context.\n")
    print("Generating SQL...\n")

    sql = generate_sql(system_prompt, user_prompt)
    print("Generated SQL:")
    print(sql)