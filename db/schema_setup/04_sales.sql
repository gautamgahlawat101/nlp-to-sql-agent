-- sales schema (run order: 4 — depends on campaign, customer, products schemas)

CREATE TABLE sales.orders (
    order_id        INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id     INTEGER NOT NULL REFERENCES customer.customers(customer_id),
    campaign_id     INTEGER REFERENCES campaign.campaigns(campaign_id),
    order_date      DATE NOT NULL,
    order_status    VARCHAR(20) NOT NULL
);
COMMENT ON COLUMN sales.orders.order_status IS 'Placed, Shipped, Delivered, Cancelled, Returned';

CREATE TABLE sales.order_items (
    order_item_id   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id        INTEGER NOT NULL REFERENCES sales.orders(order_id),
    product_id      INTEGER NOT NULL REFERENCES products.products(product_id),
    quantity        INTEGER NOT NULL,
    unit_price      DECIMAL(10,2) NOT NULL,
    discount        DECIMAL(5,2) DEFAULT 0
);

CREATE TABLE sales.transactions (
    transaction_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id            INTEGER NOT NULL REFERENCES sales.orders(order_id),
    payment_method       VARCHAR(30) NOT NULL,
    transaction_amount  DECIMAL(12,2) NOT NULL,
    transaction_date    TIMESTAMP NOT NULL
);
COMMENT ON COLUMN sales.transactions.payment_method IS 'Credit Card, Debit Card, UPI, Wallet, COD';
