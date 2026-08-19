-- products schema (run order: 3 — no dependencies)

CREATE TABLE products.product_categories (
    category_id     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category_name   VARCHAR(50) NOT NULL
);

CREATE TABLE products.products (
    product_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_name    VARCHAR(100) NOT NULL,
    category_id     INTEGER REFERENCES products.product_categories(category_id),
    sub_category    VARCHAR(50),
    brand           VARCHAR(50),
    unit_price      DECIMAL(10,2) NOT NULL
);

CREATE TABLE products.inventory (
    inventory_id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id           INTEGER NOT NULL REFERENCES products.products(product_id),
    warehouse_location   VARCHAR(50),
    stock_quantity       INTEGER DEFAULT 0,
    last_restocked_date  DATE
);
