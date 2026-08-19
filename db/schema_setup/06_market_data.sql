-- market_data schema (run order: 6 — no hard FK dependency on other schemas,
-- but is meant to be queried alongside campaign/sales on shared date ranges)
--
-- companies holds exactly one row: the same fictional retail company whose
-- campaign/customer/sales/loyalty data lives in the other 5 schemas. It is
-- modeled as publicly traded so the agent can answer cross-domain questions
-- like "did stock price move after our biggest campaign launches?" — joining
-- a transactional/marketing schema against a time-series schema on date,
-- not on a shared foreign key.

CREATE TABLE market_data.companies (
    company_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticker_symbol   VARCHAR(10) NOT NULL UNIQUE,
    company_name    VARCHAR(100) NOT NULL,
    exchange        VARCHAR(20) NOT NULL,
    sector          VARCHAR(50)
);

CREATE TABLE market_data.daily_prices (
    price_id        INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_id      INTEGER NOT NULL REFERENCES market_data.companies(company_id),
    price_date      DATE NOT NULL,
    open_price      DECIMAL(10,2) NOT NULL,
    high_price      DECIMAL(10,2) NOT NULL,
    low_price       DECIMAL(10,2) NOT NULL,
    close_price     DECIMAL(10,2) NOT NULL,
    volume          BIGINT,
    UNIQUE (company_id, price_date)
);

-- Benchmark index data (e.g. NIFTY 50), so the agent can also answer
-- relative-performance questions: "did we outperform the market that quarter?"
CREATE TABLE market_data.market_indices (
    index_id        INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    index_name      VARCHAR(50) NOT NULL,
    price_date      DATE NOT NULL,
    close_value     DECIMAL(12,2) NOT NULL,
    UNIQUE (index_name, price_date)
);
