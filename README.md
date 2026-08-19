# NLP-to-SQL Agent

A schema-aware, retrieval-augmented Text-to-SQL agent that translates natural-language
business questions into safe, validated, executable SQL across a 6-schema PostgreSQL
database (campaign, customer, sales, loyalty, products, market_data).

## Why this exists

Most "chat with your database" demos dump the entire schema into the prompt and hope
for the best. This project instead:
- Retrieves only the relevant slice of schema metadata per question (RAG over schema, not text)
- Validates every LLM-generated query with `sqlglot` before execution (SELECT-only, no hallucinated columns)
- Runs on a read-only DB role with row limits and query timeouts
- Never sends flagged-sensitive columns (PII) to the LLM
- Tracks accuracy across prompt-iteration versions on a fixed benchmark set
- Mixes transactional schemas with a time-series schema (`market_data`), so the agent has
  to handle joins on date ranges and window functions, not just foreign-key joins — a step
  up in difficulty from a purely transactional schema, and closer to what a real investor-
  relations/marketing-analytics data stack actually looks like

### The market_data schema

`market_data` holds daily OHLCV price history for the same fictional company modeled in
the other 5 schemas (as if it were publicly traded), plus a benchmark index (NIFTY 50) for
relative-performance questions. The seed script injects a small synthetic price bump in the
days following each campaign's start date, so questions like these actually have something
real to find — good both for demoing the agent and for benchmark test cases:
- "Did the stock price move in the week after our biggest campaign launches?"
- "What's the 7-day moving average of closing price around our Q2 campaigns?"
- "Did we outperform the NIFTY 50 last quarter?"

## Status

- [x] Multi-schema PostgreSQL DDL (`db/schema_setup/`)
- [x] Metadata dictionary (`data/schema_metadata.csv`)
- [x] Synthetic data generator (`db/seed_data/generate_seed_data.py`)
- [x] Market data generator (`db/seed_data/generate_market_data.py`)
- [ ] Metadata retriever
- [ ] Prompt builder
- [ ] LLM client (OpenRouter primary, Gemini fallback)
- [ ] SQL validator
- [ ] Executor + conversation manager
- [ ] Streamlit UI
- [ ] Benchmark suite

## Setup

1. Create a PostgreSQL database (Neon / Supabase / Aiven free tier, or local Postgres).
2. Copy `.env.example` to `.env` and fill in your DB credentials and LLM API key.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Apply the schema, in order:
   ```bash
   psql "$DATABASE_URL" -f db/schema_setup/00_create_schemas.sql
   psql "$DATABASE_URL" -f db/schema_setup/01_campaign.sql
   psql "$DATABASE_URL" -f db/schema_setup/02_customer.sql
   psql "$DATABASE_URL" -f db/schema_setup/03_products.sql
   psql "$DATABASE_URL" -f db/schema_setup/04_sales.sql
   psql "$DATABASE_URL" -f db/schema_setup/05_loyalty.sql
   psql "$DATABASE_URL" -f db/schema_setup/06_market_data.sql
   ```
5. Seed synthetic data (in this order — market data reads campaign dates to inject
   its correlation signal, so it must run second):
   ```bash
   python db/seed_data/generate_seed_data.py
   python db/seed_data/generate_market_data.py
   ```

## Security notes

- The DB user in `.env` should be granted `SELECT` only, across all 5 schemas — never
  write/DDL privileges. Create it explicitly rather than reusing an admin role.
- `.env` is gitignored — never commit real credentials.
