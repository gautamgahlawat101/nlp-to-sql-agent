"""
Central config. Everything pulls from environment variables (.env locally,
Streamlit secrets in the cloud) — no credentials ever hardcoded here.
"""

import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

import os
from dotenv import load_dotenv

load_dotenv()

# --- Database ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "nlp_sql_agent_db")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{quote_plus(DB_PASSWORD or '')}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"
)

AGENT_DB_USER = os.getenv("AGENT_DB_USER")
AGENT_DB_PASSWORD = os.getenv("AGENT_DB_PASSWORD")

AGENT_DATABASE_URL = (
    f"postgresql+psycopg2://{AGENT_DB_USER}:{quote_plus(AGENT_DB_PASSWORD or '')}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"
)


# --- LLM Provider ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Agent behavior / guardrails ---
MAX_ROW_LIMIT = int(os.getenv("MAX_ROW_LIMIT", 200))
QUERY_TIMEOUT_SECONDS = int(os.getenv("QUERY_TIMEOUT_SECONDS", 10))
MAX_LLM_RETRIES = int(os.getenv("MAX_LLM_RETRIES", 2))

# --- Paths ---
METADATA_CSV_PATH = "data/schema_metadata.csv"
FEW_SHOT_EXAMPLES_PATH = "data/few_shot_examples.json"