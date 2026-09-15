"""
Generates synthetic data across all 5 schemas using Faker and inserts it
via SQLAlchemy. Run this AFTER the DDL scripts (00-05) have been applied.

Usage:
    python db/seed_data/generate_seed_data.py
"""
import random
import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from faker import Faker
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from db.connection import get_engine

fake = Faker()
engine = get_engine()

N_CUSTOMERS = 200
N_PRODUCTS = 60
N_CAMPAIGNS = 15
N_ORDERS = 500


def run(sql, params=None, retries=3):
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            with engine.begin() as conn:
                return conn.execute(text(sql), params or {})
        except OperationalError as e:
            last_error = e
            print(f"  Connection hiccup (attempt {attempt}/{retries}), retrying...")
            time.sleep(2 * attempt)
    raise last_error


def seed_campaigns():
    channels = ["Digital", "Social", "Email", "Print", "TV"]
    channel_ids = []
    for ch in channels:
        r = run(
            "INSERT INTO campaign.campaign_channels (channel_name, channel_type) "
            "VALUES (:name, :type) RETURNING channel_id",
            {"name": f"{ch} Ads", "type": ch},
        )
        channel_ids.append(r.scalar())

    campaign_ids = []
    for _ in range(N_CAMPAIGNS):
        start = fake.date_between(start_date="-1y", end_date="today")
        r = run(
            "INSERT INTO campaign.campaigns "
            "(campaign_name, channel_id, start_date, end_date, budget, status) "
            "VALUES (:name, :ch, :start, :end, :budget, :status) RETURNING campaign_id",
            {
                "name": fake.catch_phrase(),
                "ch": random.choice(channel_ids),
                "start": start,
                "end": fake.date_between(start_date=start, end_date="+30d"),
                "budget": round(random.uniform(5000, 100000), 2),
                "status": random.choice(["Planned", "Active", "Paused", "Completed"]),
            },
        )
        campaign_ids.append(r.scalar())

    for cid in campaign_ids:
        for _ in range(random.randint(3, 10)):
            run(
                "INSERT INTO campaign.campaign_performance "
                "(campaign_id, perf_date, impressions, clicks, spend) "
                "VALUES (:cid, :date, :impr, :clicks, :spend)",
                {
                    "cid": cid,
                    "date": fake.date_between(start_date="-1y", end_date="today"),
                    "impr": random.randint(1000, 50000),
                    "clicks": random.randint(10, 2000),
                    "spend": round(random.uniform(50, 2000), 2),
                },
            )
    return campaign_ids


def seed_customers():
    customer_ids = []
    for _ in range(N_CUSTOMERS):
        r = run(
            "INSERT INTO customer.customers "
            "(first_name, last_name, email, phone, signup_date, city, state, country) "
            "VALUES (:fn, :ln, :email, :phone, :signup, :city, :state, :country) "
            "RETURNING customer_id",
            {
                "fn": fake.first_name(),
                "ln": fake.last_name(),
                "email": fake.unique.email(),
                "phone": fake.phone_number()[:20],
                "signup": fake.date_between(start_date="-3y", end_date="today"),
                "city": fake.city(),
                "state": fake.state(),
                "country": "India",
            },
        )
        customer_ids.append(r.scalar())

    segments = [
        ("High Value", "Spent over 50000 in last 90 days"),
        ("At Risk", "No purchase in last 120 days"),
        ("New", "Signed up in last 30 days"),
    ]
    segment_ids = []
    for name, desc in segments:
        r = run(
            "INSERT INTO customer.customer_segments (segment_name, criteria_description) "
            "VALUES (:name, :desc) RETURNING segment_id",
            {"name": name, "desc": desc},
        )
        segment_ids.append(r.scalar())

    for cust_id in customer_ids:
        if random.random() < 0.6:
            run(
                "INSERT INTO customer.customer_segment_map (customer_id, segment_id, assigned_date) "
                "VALUES (:cust, :seg, :date)",
                {
                    "cust": cust_id,
                    "seg": random.choice(segment_ids),
                    "date": fake.date_between(start_date="-1y", end_date="today"),
                },
            )
    return customer_ids


def seed_products():
    categories = ["Electronics", "Apparel", "Groceries", "Home & Kitchen", "Beauty"]
    category_ids = []
    for cat in categories:
        r = run(
            "INSERT INTO products.product_categories (category_name) VALUES (:name) "
            "RETURNING category_id",
            {"name": cat},
        )
        category_ids.append(r.scalar())

    product_ids = []
    for _ in range(N_PRODUCTS):
        r = run(
            "INSERT INTO products.products "
            "(product_name, category_id, sub_category, brand, unit_price) "
            "VALUES (:name, :cat, :sub, :brand, :price) RETURNING product_id",
            {
                "name": fake.catch_phrase(),
                "cat": random.choice(category_ids),
                "sub": fake.word().capitalize(),
                "brand": fake.company(),
                "price": round(random.uniform(199, 9999), 2),
            },
        )
        pid = r.scalar()
        product_ids.append(pid)
        run(
            "INSERT INTO products.inventory "
            "(product_id, warehouse_location, stock_quantity, last_restocked_date) "
            "VALUES (:pid, :loc, :qty, :date)",
            {
                "pid": pid,
                "loc": f"{fake.city()} DC",
                "qty": random.randint(0, 1000),
                "date": fake.date_between(start_date="-90d", end_date="today"),
            },
        )
    return product_ids


def seed_sales(customer_ids, campaign_ids, product_ids):
    for _ in range(N_ORDERS):
        order_date = fake.date_between(start_date="-1y", end_date="today")
        r = run(
            "INSERT INTO sales.orders (customer_id, campaign_id, order_date, order_status) "
            "VALUES (:cust, :camp, :date, :status) RETURNING order_id",
            {
                "cust": random.choice(customer_ids),
                "camp": random.choice(campaign_ids) if random.random() < 0.4 else None,
                "date": order_date,
                "status": random.choice(
                    ["Placed", "Shipped", "Delivered", "Cancelled", "Returned"]
                ),
            },
        )
        order_id = r.scalar()

        total = 0
        for _ in range(random.randint(1, 4)):
            price = round(random.uniform(199, 9999), 2)
            qty = random.randint(1, 3)
            discount = round(random.choice([0, 0, 0, 5, 10, 15]), 2)
            run(
                "INSERT INTO sales.order_items "
                "(order_id, product_id, quantity, unit_price, discount) "
                "VALUES (:oid, :pid, :qty, :price, :disc)",
                {
                    "oid": order_id,
                    "pid": random.choice(product_ids),
                    "qty": qty,
                    "price": price,
                    "disc": discount,
                },
            )
            total += price * qty * (1 - discount / 100)

        run(
            "INSERT INTO sales.transactions "
            "(order_id, payment_method, transaction_amount, transaction_date) "
            "VALUES (:oid, :method, :amount, :date)",
            {
                "oid": order_id,
                "method": random.choice(
                    ["Credit Card", "Debit Card", "UPI", "Wallet", "COD"]
                ),
                "amount": round(total, 2),
                "date": order_date,
            },
        )


def seed_loyalty(customer_ids):
    tiers = ["Bronze", "Silver", "Gold", "Platinum"]
    loyalty_ids = []
    for cust_id in customer_ids:
        if random.random() < 0.7:
            r = run(
                "INSERT INTO loyalty.loyalty_accounts "
                "(customer_id, tier, points_balance, enrollment_date) "
                "VALUES (:cust, :tier, :points, :date) RETURNING loyalty_id",
                {
                    "cust": cust_id,
                    "tier": random.choice(tiers),
                    "points": random.randint(0, 5000),
                    "date": fake.date_between(start_date="-2y", end_date="today"),
                },
            )
            loyalty_ids.append(r.scalar())

    reward_defs = [
        ("Free Shipping Voucher", 500, "Discount"),
        ("10% Off Coupon", 1000, "Discount"),
        ("Free Gift", 2000, "Freebie"),
        ("Cashback 200", 1500, "Cashback"),
    ]
    for name, pts, rtype in reward_defs:
        run(
            "INSERT INTO loyalty.loyalty_rewards (reward_name, points_required, reward_type) "
            "VALUES (:name, :pts, :type)",
            {"name": name, "pts": pts, "type": rtype},
        )

    for lid in loyalty_ids:
        for _ in range(random.randint(1, 5)):
            change = random.choice([50, 100, 200, -500, -1000])
            run(
                "INSERT INTO loyalty.loyalty_transactions "
                "(loyalty_id, points_change, reason, txn_date) "
                "VALUES (:lid, :change, :reason, :date)",
                {
                    "lid": lid,
                    "change": change,
                    "reason": "Purchase reward" if change > 0 else "Redeemed for voucher",
                    "date": fake.date_time_between(start_date="-1y", end_date="now"),
                },
            )


if __name__ == "__main__":
    print("Seeding campaign schema...")
    campaign_ids = seed_campaigns()
    print("Seeding customer schema...")
    customer_ids = seed_customers()
    print("Seeding products schema...")
    product_ids = seed_products()
    print("Seeding sales schema...")
    seed_sales(customer_ids, campaign_ids, product_ids)
    print("Seeding loyalty schema...")
    seed_loyalty(customer_ids)
    print("Done.")
