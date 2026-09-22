"""
agent/metadata_retriever.py

The "librarian": given a natural-language question, scans data/schema_metadata.csv
and returns only the schema/table/column rows relevant to that question — instead
of dumping the entire 91-column, 18-table schema into every LLM prompt.

Usage (standalone test):
    python agent/metadata_retriever.py "top customers by revenue"
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
from rapidfuzz import fuzz

from config.settings import METADATA_CSV_PATH

_TIER_WEIGHT = {"high": 1.15, "medium": 1.0, "low": 0.85}


def _load_metadata():
    df = pd.read_csv(METADATA_CSV_PATH)
    df = df.fillna("")
    # One combined "searchable text" field per row, pulling together every place
    # a business term might show up: the column's own name, its table, its plain-
    # English description, and the informal synonyms a real user might type.
    df["search_text"] = (
        df["column_name"].str.replace("_", " ")
        + " " + df["table_name"].str.replace("_", " ")
        + " " + df["description"]
        + " " + df["business_synonyms"]
    ).str.lower()
    return df


_METADATA = _load_metadata()


def retrieve_relevant_columns(question: str, top_n: int = 20, min_score: float = 40.0):
    """
    Given a natural-language question, return the most relevant rows from the
    metadata CSV, ranked by fuzzy match score against the question (nudged by
    each column's relevance_tier).

    Deliberately simple keyword/fuzzy matching, not embeddings — good enough at
    this schema size (91 columns), fast, free, and far easier to debug than a
    vector search black box. Upgrade path exists later if retrieval accuracy
    becomes the bottleneck.
    """
    question_lower = question.lower()
    scored = []

    for _, row in _METADATA.iterrows():
        score = fuzz.token_set_ratio(question_lower, row["search_text"])
        score *= _TIER_WEIGHT.get(row["relevance_tier"], 1.0)
        if score >= min_score:
            scored.append((score, row))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_rows = [row for _, row in scored[:top_n]]

    # Always include every primary/foreign key column for any table that made
    # the shortlist, even if that ID column didn't score highly on its own —
    # the LLM needs those to actually write correct JOINs.
    matched_tables = {(r["schema_name"], r["table_name"]) for r in top_rows}
    key_rows = _METADATA[
        _METADATA.apply(
            lambda r: (r["schema_name"], r["table_name"]) in matched_tables
            and (r["is_primary_key"] == "Y" or r["is_foreign_key"] == "Y"),
            axis=1,
        )
    ]

    combined = pd.concat([pd.DataFrame(top_rows), key_rows]).drop_duplicates(
        subset=["schema_name", "table_name", "column_name"]
    )

    return combined.drop(columns=["search_text"]).to_dict(orient="records")


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "top customers by revenue"
    results = retrieve_relevant_columns(q)
    print(f"Question: {q}")
    print(f"Retrieved {len(results)} relevant columns:\n")
    for r in results:
        print(f"  {r['schema_name']}.{r['table_name']}.{r['column_name']}  —  {r['description']}")