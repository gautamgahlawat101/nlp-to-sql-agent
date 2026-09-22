"""
agent/llm_client.py

Provider-agnostic wrapper around whichever LLM generates the SQL. OpenRouter
is the primary provider (free-tier models, OpenAI-compatible API) — chosen as
a config value in .env rather than hardcoded, since free-tier model
availability shifts over time and swapping providers should never require
touching this file's logic.

Usage:
    from agent.llm_client import generate_sql
    raw_response = generate_sql(system_prompt, user_prompt)
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import LLM_PROVIDER, OPENROUTER_API_KEY, OPENROUTER_MODEL

_client = None


def _get_openrouter_client():
    global _client
    if _client is None:
        if not OPENROUTER_API_KEY:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set in .env — sign up at openrouter.ai "
                "and generate a key before running the agent."
            )
        _client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)
    return _client


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def generate_sql(system_prompt: str, user_prompt: str) -> str:
    """
    Sends the assembled prompt to the configured LLM provider and returns the
    raw text response. Extracting/validating the SQL from that text happens
    later, in Step 14's sql_validator.py — not this function's job.
    """
    if LLM_PROVIDER == "openrouter":
        client = _get_openrouter_client()
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
        )
        return response.choices[0].message.content
    elif LLM_PROVIDER == "gemini":
        raise NotImplementedError(
            "Gemini fallback isn't wired up yet — set LLM_PROVIDER=openrouter in .env for now."
        )
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER!r}")


if __name__ == "__main__":
    print("Sending test request to LLM...")
    result = generate_sql("You are a helpful assistant.", "Reply with exactly the word: pong")
    print(f"Response: {result}")