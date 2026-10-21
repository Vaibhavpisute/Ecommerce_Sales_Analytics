-- Star schema for the analytics database (analytics_db).
-- Created by notebooks/01_data_cleaning.ipynb. Safe to run again: it drops the tables first.
-- Grain: fact_orders = 1 row per order, fact_order_items = 1 row per item sold,
--        fact_payments = 1 row per payment, fact_reviews = 1 row per order (latest review).

DROP TABLE IF EXISTS fact_reviews, fact_payments, fact_order_items, fact_orders,
                     dim_seller, dim_product, dim_customer, dim_date CASCADE;

CREATE TABLE dim_date (
    date_key            INT PRIMARY KEY,        -- yyyymmdd
    full_date           DATE NOT NULL UNIQUE,
    year                INT NOT NULL,
    quarter             INT NOT NULL,
    month               INT NOT NULL,
    month_name          TEXT NOT NULL,
    year_month          TEXT NOT NULL,          -- 'YYYY-MM'
    day                 INT NOT NULL,
    day_of_week         INT NOT NULL,           -- 1 = Monday ... 7 = Sunday
    day_name            TEXT NOT NULL,
    week_of_year        INT NOT NULL,
    is_weekend          BOOLEAN NOT NULL,
    in_analysis_period  BOOLEAN NOT NULL        -- full months 2017-01 to 2018-08 (see notebook 01)
);

CREATE TABLE dim_customer (
    customer_unique_id  TEXT PRIMARY KEY,       -- one real person (use this for repeat / cohort / RFM)
    city                TEXT,
    state               TEXT,
    zip_code_prefix     TEXT                    -- city, state and zip of the customer's latest order
);

CREATE TABLE dim_product (
    product_id          TEXT PRIMARY KEY,
    category_pt         TEXT,
    category_en         TEXT NOT NULL,
    weight_g            DOUBLE PRECISION,
    photos_qty          INT
);

CREATE TABLE dim_seller (
    seller_id           TEXT PRIMARY KEY,
    city                TEXT,
    state               TEXT
);

CREATE TABLE fact_orders (
    order_id                TEXT PRIMARY KEY,
    customer_id             TEXT NOT NULL,      -- id of the order (changes for each order)
    customer_unique_id      TEXT NOT NULL REFERENCES dim_customer (customer_unique_id),
    customer_state          TEXT,
    customer_city           TEXT,
    order_status            TEXT NOT NULL,
    purchase_ts             TIMESTAMP NOT NULL,
    purchase_date           DATE NOT NULL,
    purchase_date_key       INT NOT NULL REFERENCES dim_date (date_key),
    approved_ts             TIMESTAMP,
    carrier_ts              TIMESTAMP,
    delivered_ts            TIMESTAMP,
    estimated_delivery_ts   TIMESTAMP,
    item_count              INT NOT NULL,
    items_value             NUMERIC(12, 2) NOT NULL,   -- sum of item prices (revenue, without freight)
    freight_value           NUMERIC(12, 2) NOT NULL,
    payment_value           NUMERIC(12, 2),
    max_installments        INT,
    main_payment_type       TEXT,
    review_score            NUMERIC(3, 2),
    delivery_days           NUMERIC(8, 2),             -- only for status 'delivered' with a delivery date
    delay_days              NUMERIC(8, 2),             -- delivered date minus estimated date (> 0 = late)
    is_late                 BOOLEAN,
    has_items               BOOLEAN NOT NULL,
    is_valid_sale           BOOLEAN NOT NULL,          -- has items and status not canceled / unavailable
    flag_ts_inconsistent    BOOLEAN NOT NULL,          -- carrier date before purchase, or delivery before carrier date
    flag_value_outlier      BOOLEAN NOT NULL           -- items_value above the IQR upper fence
);

CREATE TABLE fact_order_items (
    order_id            TEXT NOT NULL REFERENCES fact_orders (order_id),
    order_item_id       INT NOT NULL,
    product_id          TEXT NOT NULL REFERENCES dim_product (product_id),
    seller_id           TEXT NOT NULL REFERENCES dim_seller (seller_id),
    customer_unique_id  TEXT NOT NULL,
    purchase_date_key   INT NOT NULL REFERENCES dim_date (date_key),
    order_status        TEXT NOT NULL,
    price               NUMERIC(12, 2) NOT NULL,
    freight_value       NUMERIC(12, 2) NOT NULL,
    flag_price_outlier  BOOLEAN NOT NULL,
    PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE fact_payments (
    order_id              TEXT NOT NULL REFERENCES fact_orders (order_id),
    payment_sequential    INT NOT NULL,
    payment_type          TEXT NOT NULL,
    payment_installments  INT NOT NULL,
    payment_value         NUMERIC(12, 2) NOT NULL,
    PRIMARY KEY (order_id, payment_sequential)
);

CREATE TABLE fact_reviews (
    order_id        TEXT PRIMARY KEY REFERENCES fact_orders (order_id),
    review_id       TEXT NOT NULL,
    review_score    INT NOT NULL,
    creation_ts     TIMESTAMP,
    answer_ts       TIMESTAMP
);

-- Indexes for joins and the common filters in the 15 queries
CREATE INDEX ix_fact_orders_customer   ON fact_orders (customer_unique_id);
CREATE INDEX ix_fact_orders_date       ON fact_orders (purchase_date_key);
CREATE INDEX ix_fact_orders_status     ON fact_orders (order_status);
CREATE INDEX ix_fact_orders_state      ON fact_orders (customer_state);
CREATE INDEX ix_items_product          ON fact_order_items (product_id);
CREATE INDEX ix_items_seller           ON fact_order_items (seller_id);
CREATE INDEX ix_items_date             ON fact_order_items (purchase_date_key);
CREATE INDEX ix_product_category       ON dim_product (category_en);
CREATE INDEX ix_customer_state         ON dim_customer (state);
