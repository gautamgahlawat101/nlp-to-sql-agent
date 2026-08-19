"""
Seeds the market_data schema:
  1. One company row — the same fictional retail business as the other schemas.
  2. Daily OHLCV price history for that company, generated as a random walk
     with a small injected upward drift in the days following each campaign's
     start date (so "does marketing spend correlate with stock price" queries
     actually have something real to find — useful for demoing/benchmarking
     the agent, not just filler data).
  3. A benchmark index (NIFTY 50) for relative-performance questions. Tries a
     real historical pull via yfinance first; falls back to a synthetic
     random walk if yfinance/network isn't available, so this script never
     hard-fails just because you're offline.

IMPORTANT: run this AFTER generate_seed_data.py — it reads campaign start
dates from campaign.campaigns to inject the correlation signal.

Usage:
    python db/seed_data/generate_market_data.py
"""
import sys
import os
import random
from datetime import timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sqlalchemy import text
from db.connection import get_engine

engine = get_engine()

TICKER = "NVMT"
COMPANY_NAME = "NovaMart Retail Inc."
EXCHANGE = "NASDAQ"
SECTOR = "Retail"
START_PRICE = 150.00
DAILY_DRIFT = 0.0004       # baseline mean daily return
DAILY_VOL = 0.015          # daily volatility
CAMPAIGN_BUMP = 0.0035     # extra mean return for 5 trading days after a campaign starts
CAMPAIGN_BUMP_WINDOW = 5


def run(sql, params=None):
    with engine.begin() as conn:
        return conn.execute(text(sql), params or {})


def business_days_between(start_date, end_date):
    days = []
    d = start_date
    while d <= end_date:
        if d.weekday() < 5:  # Mon-Fri
            days.append(d)
        d += timedelta(days=1)
    return days


def seed_company():
    r = run(
        "INSERT INTO market_data.companies (ticker_symbol, company_name, exchange, sector) "
        "VALUES (:ticker, :name, :exch, :sector) RETURNING company_id",
        {"ticker": TICKER, "name": COMPANY_NAME, "exch": EXCHANGE, "sector": SECTOR},
    )
    return r.scalar()


def get_campaign_start_dates():
    result = run("SELECT start_date FROM campaign.campaigns")
    return [row[0] for row in result.fetchall()]


def seed_daily_prices(company_id, campaign_starts):
    if not campaign_starts:
        print("No campaigns found — run generate_seed_data.py first. Skipping price correlation signal.")
    end_date = max(campaign_starts) if campaign_starts else None
    from datetime import date
    today = date.today()
    start_date = today - timedelta(days=730)  # 2 years of history

    days = business_days_between(start_date, today)
    price = START_PRICE

    # Precompute which trading days fall inside a post-campaign bump window
    bump_days = set()
    for cstart in campaign_starts:
        for offset in range(1, CAMPAIGN_BUMP_WINDOW + 1):
            bump_days.add(cstart + timedelta(days=offset))

    for d in days:
        mean_return = DAILY_DRIFT + (CAMPAIGN_BUMP if d in bump_days else 0)
        daily_return = random.gauss(mean_return, DAILY_VOL)
        close = round(price * (1 + daily_return), 2)
        open_price = round(price * (1 + random.gauss(0, 0.004)), 2)
        high = round(max(open_price, close) * (1 + abs(random.gauss(0, 0.003))), 2)
        low = round(min(open_price, close) * (1 - abs(random.gauss(0, 0.003))), 2)
        volume = random.randint(500_000, 4_000_000)

        run(
            "INSERT INTO market_data.daily_prices "
            "(company_id, price_date, open_price, high_price, low_price, close_price, volume) "
            "VALUES (:cid, :date, :open, :high, :low, :close, :vol) "
            "ON CONFLICT (company_id, price_date) DO NOTHING",
            {
                "cid": company_id,
                "date": d,
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "vol": volume,
            },
        )
        price = close


def seed_market_index():
    from datetime import date
    today = date.today()
    start_date = today - timedelta(days=730)
    index_name = "NIFTY 50"

    try:
        import yfinance as yf
        hist = yf.Ticker("^NSEI").history(start=start_date, end=today)
        if hist.empty:
            raise ValueError("yfinance returned no data")
        for idx, row in hist.iterrows():
            run(
                "INSERT INTO market_data.market_indices (index_name, price_date, close_value) "
                "VALUES (:name, :date, :close) ON CONFLICT (index_name, price_date) DO NOTHING",
                {"name": index_name, "date": idx.date(), "close": round(float(row["Close"]), 2)},
            )
        print(f"Seeded {index_name} from live yfinance data.")
        return
    except Exception as e:
        print(f"yfinance pull failed ({e}) — falling back to synthetic index data.")

    days = business_days_between(start_date, today)
    value = 22000.00
    for d in days:
        value = round(value * (1 + random.gauss(0.0003, 0.009)), 2)
        run(
            "INSERT INTO market_data.market_indices (index_name, price_date, close_value) "
            "VALUES (:name, :date, :close) ON CONFLICT (index_name, price_date) DO NOTHING",
            {"name": index_name, "date": d, "close": value},
        )
    print(f"Seeded {index_name} with synthetic data.")


if __name__ == "__main__":
    print("Seeding market_data schema...")
    company_id = seed_company()
    campaign_starts = get_campaign_start_dates()
    seed_daily_prices(company_id, campaign_starts)
    seed_market_index()
    print("Done.")
