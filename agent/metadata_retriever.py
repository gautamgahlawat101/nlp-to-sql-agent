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
_WORD_MATCH_THRESHOLD = 80.0  # how close two individual words must be to count as a match
_STOPWORDS = {
    "top", "by", "the", "a", "an", "of", "in", "for", "this", "that", "is",
    "are", "was", "were", "to", "and", "or", "with", "on", "at", "from",
}


def _load_metadata():
    df = pd.read_csv(METADATA_CSV_PATH)
    df = df.fillna("")
    df = df[df["sensitive_flag"] != "Y"].reset_index(drop=True)  # PII never reaches the LLM
    combined = (
        df["column_name"].str.replace("_", " ")
        + " " + df["table_name"].str.replace("_", " ")
        + " " + df["business_synonyms"].str.replace(";", " ")
    ).str.lower()
    df["search_words"] = combined.apply(lambda s: set(s.split()))
    df["is_date_type"] = df["data_type"].str.upper().str.contains("DATE|TIMESTAMP", regex=True)
    return df


_METADATA = _load_metadata()


def retrieve_relevant_columns(question: str, top_n: int = 20, min_score: float = 1.0):
    question_words = [w for w in question.lower().split() if w not in _STOPWORDS]
    scored = []
    for _, row in _METADATA.iterrows():
        match_score = 0.0
        for qw in question_words:
            best = max((fuzz.ratio(qw, sw) for sw in row["search_words"]), default=0)
            if best >= _WORD_MATCH_THRESHOLD:
                match_score += best
        match_score *= _TIER_WEIGHT.get(row["relevance_tier"], 1.0)
        if match_score >= min_score:
            scored.append((match_score, row))
    scored.sort(key=lambda x: x[0], reverse=True)
    top_rows = [row for _, row in scored[:top_n]]
    matched_tables = {(r["schema_name"], r["table_name"]) for r in top_rows}

    # market_data's 3 tables are always used together for stock/comparison
    # questions, even when the wording only overlaps with one of them (e.g.
    # "did we outperform NIFTY" never says "stock" or "company"). Pull in the
    # rest of market_data whenever any part of it matched, so the LLM sees the
    # full picture instead of guessing or refusing to answer.
    if any(s == "market_data" for s, _ in matched_tables):
        matched_tables.update(
            (s, t) for s, t in _METADATA[["schema_name", "table_name"]].drop_duplicates().values
            if s == "market_data"
        )

    support_rows = _METADATA[
        _METADATA.apply(
            lambda r: (r["schema_name"], r["table_name"]) in matched_tables
            and (
                r["is_primary_key"] == "Y"
                or r["is_foreign_key"] == "Y"
                or r["is_date_type"]
                or r["schema_name"] == "market_data"
            ),
            axis=1,
        )
    ]
    combined = pd.concat([pd.DataFrame(top_rows), support_rows]).drop_duplicates(
        subset=["schema_name", "table_name", "column_name"]
    )
    return combined.drop(columns=["search_words", "is_date_type"]).to_dict(orient="records")


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "top customers by revenue"
    results = retrieve_relevant_columns(q)
    print(f"Question: {q}")
    print(f"Retrieved {len(results)} relevant columns:\n")
    for r in results:
        print(f"  {r['schema_name']}.{r['table_name']}.{r['column_name']}  —  {r['description']}")