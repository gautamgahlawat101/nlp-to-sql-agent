-- customer schema (run order: 2 — no dependencies)

CREATE TABLE customer.customers (
    customer_id     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    first_name      VARCHAR(50) NOT NULL,
    last_name       VARCHAR(50) NOT NULL,
    email           VARCHAR(100) NOT NULL UNIQUE,
    phone           VARCHAR(20),
    signup_date     DATE NOT NULL,
    city            VARCHAR(50),
    state           VARCHAR(50),
    country         VARCHAR(50)
);

CREATE TABLE customer.customer_segments (
    segment_id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    segment_name          VARCHAR(50) NOT NULL,
    criteria_description  VARCHAR(255)
);

CREATE TABLE customer.customer_segment_map (
    customer_id     INTEGER NOT NULL REFERENCES customer.customers(customer_id),
    segment_id      INTEGER NOT NULL REFERENCES customer.customer_segments(segment_id),
    assigned_date   DATE NOT NULL,
    PRIMARY KEY (customer_id, segment_id)  
);
