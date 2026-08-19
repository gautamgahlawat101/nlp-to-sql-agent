-- loyalty schema (run order: 5 — depends on customer schema)

CREATE TABLE loyalty.loyalty_accounts (
    loyalty_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id     INTEGER NOT NULL REFERENCES customer.customers(customer_id),
    tier            VARCHAR(20) NOT NULL,
    points_balance  INTEGER DEFAULT 0,
    enrollment_date DATE NOT NULL
);
COMMENT ON COLUMN loyalty.loyalty_accounts.tier IS 'Bronze, Silver, Gold, Platinum';

CREATE TABLE loyalty.loyalty_rewards (
    reward_id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    reward_name       VARCHAR(100) NOT NULL,
    points_required   INTEGER NOT NULL,
    reward_type       VARCHAR(30)
);
COMMENT ON COLUMN loyalty.loyalty_rewards.reward_type IS 'Discount, Freebie, Cashback, Upgrade';

CREATE TABLE loyalty.loyalty_transactions (
    loyalty_txn_id    INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    loyalty_id        INTEGER NOT NULL REFERENCES loyalty.loyalty_accounts(loyalty_id),
    points_change     INTEGER NOT NULL,
    reason            VARCHAR(100),
    txn_date          TIMESTAMP NOT NULL
);
COMMENT ON COLUMN loyalty.loyalty_transactions.points_change IS 'positive = earned, negative = redeemed';
