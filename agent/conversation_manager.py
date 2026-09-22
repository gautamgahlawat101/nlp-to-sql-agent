"""
agent/conversation_manager.py

Ties the full pipeline together: retrieval -> prompt building -> LLM
generation -> validation -> execution. Handles the two things that go wrong
in a one-shot pipeline: a validation failure (fed back to the LLM to
self-correct, up to MAX_LLM_RETRIES times) and a genuinely ambiguous question
(the LLM is instructed to ask a clarifying question instead of guessing).
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.metadata_retriever import retrieve_relevant_columns
from agent.prompt_builder import build_prompt
from agent.llm_client import generate_sql
from agent.sql_validator import validate_sql, ValidationError
from agent.executor import execute_query
from config.settings import MAX_LLM_RETRIES


def ask(question: str) -> dict:
    """
    Runs the full pipeline for one question. Returns one of:
      {"status": "success", "sql": ..., "rows": [...]}
      {"status": "clarify", "question": "..."}
      {"status": "error", "message": "..."}
    """
    columns = retrieve_relevant_columns(question)
    system_prompt, user_prompt = build_prompt(question, columns)

    last_error = None

    for attempt in range(1, MAX_LLM_RETRIES + 2):
        raw_response = generate_sql(system_prompt, user_prompt)

        if raw_response.strip().upper().startswith("CLARIFY:"):
            clarifying_question = raw_response.split(":", 1)[1].strip()
            return {"status": "clarify", "question": clarifying_question}

        try:
            sql = validate_sql(raw_response)
            rows = execute_query(sql)
            return {"status": "success", "sql": sql, "rows": rows}
        except ValidationError as e:
            last_error = str(e)
            print(f"  Attempt {attempt} failed validation: {last_error}")
            print("  Asking the LLM to fix it...")
            user_prompt = (
                f"Question: {question}\n\n"
                f"Your previous SQL was rejected for this reason: {last_error}\n"
                f"Please correct it and respond with ONLY the corrected SQL."
            )
        except Exception as e:
            last_error = str(e)
            print(f"  Attempt {attempt} failed to execute: {last_error}")
            break

    return {"status": "error", "message": f"Failed after retries: {last_error}"}


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "top customers by revenue this year"
    print(f"Question: {q}\n")

    result = ask(q)

    if result["status"] == "success":
        print(f"SQL: {result['sql']}\n")
        print(f"Retrieved {len(result['rows'])} rows:")
        for row in result["rows"]:
            print(f"  {row}")
    elif result["status"] == "clarify":
        print(f"Clarifying question needed: {result['question']}")
    else:
        print(f"Error: {result['message']}")