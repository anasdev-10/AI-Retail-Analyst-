-- =============================================================================
-- FILE: 01_schema.sql
-- PURPOSE: Creates the retail_dw schema and all 9 tables for the Kimball-style
--          dimensional star schema retail data warehouse.
--          Run this FIRST before any seed data scripts.
-- AUTHOR:  Generated for MCP-Based SQL Data Analyst Assistant (GEN-AI Assignment 3)
-- USAGE:   psql -U postgres -d retail_dw_db -f 01_schema.sql
-- =============================================================================

-- === SECTION: SCHEMA SETUP ===

CREATE SCHEMA IF NOT EXISTS retail_dw;
SET search_path TO retail_dw;


-- =============================================================================
-- === SECTION: DIMENSION TABLES ===
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Table: dim_date
-- Grain: One row per calendar day from 2024-01-01 to 2026-12-31.
-- Purpose: Central time dimension for all fact tables. Date key uses YYYYMMDD
--          integer format for efficient joining. Includes fiscal year/quarter
--          support (fiscal year starts July 1).
-- -----------------------------------------------------------------------------
CREATE TABLE dim_date (
    date_key            INTEGER      PRIMARY KEY,          -- YYYYMMDD format
    full_date           DATE         NOT NULL UNIQUE,
    day_of_week         SMALLINT     NOT NULL,             -- 1=Mon ... 7=Sun (ISO)
    day_name            VARCHAR(10)  NOT NULL,
    day_of_month        SMALLINT     NOT NULL,
    week_of_year        SMALLINT     NOT NULL,
    month_number        SMALLINT     NOT NULL,
    month_name          VARCHAR(12)  NOT NULL,
    quarter_number      SMALLINT     NOT NULL,
    year_number         SMALLINT     NOT NULL,
    is_weekend          BOOLEAN      NOT NULL,
    fiscal_year         SMALLINT     NOT NULL,             -- Fiscal year starts July 1
    fiscal_quarter      SMALLINT     NOT NULL              -- Fiscal quarter (1-4)
);

-- -----------------------------------------------------------------------------
-- Table: dim_product
-- Grain: One row per product SKU (with optional SCD Type 2 support via flags).
-- Purpose: Denormalized product dimension. Category and subcategory are stored
--          inline (no separate category table) for simple star-schema queries.
--          Supports 10 categories x 100 subcategories x 100 products = 10,000 rows.
-- -----------------------------------------------------------------------------
CREATE TABLE dim_product (
    product_key             BIGSERIAL    PRIMARY KEY,
    product_code            VARCHAR(30)  NOT NULL UNIQUE,
    product_name            VARCHAR(150) NOT NULL,
    category_name           VARCHAR(80)  NOT NULL,
    subcategory_name        VARCHAR(80)  NOT NULL,
    brand_name              VARCHAR(80)  NOT NULL,
    supplier_name           VARCHAR(120) NOT NULL,
    unit_size               VARCHAR(40),
    color                   VARCHAR(40),
    standard_cost           NUMERIC(12,2) NOT NULL,
    list_price              NUMERIC(12,2) NOT NULL,
    launch_date             DATE         NOT NULL,
    is_active               BOOLEAN      NOT NULL DEFAULT TRUE,
    effective_start_date    DATE         NOT NULL DEFAULT DATE '2024-01-01',
    effective_end_date      DATE,                          -- NULL = currently active
    current_flag            BOOLEAN      NOT NULL DEFAULT TRUE
);

-- -----------------------------------------------------------------------------
-- Table: dim_store
-- Grain: One row per physical store location.
-- Purpose: Stores retail locations across Pakistan (10 stores, multiple regions).
--          Supports regional and city-level breakdowns in analytical queries.
-- -----------------------------------------------------------------------------
CREATE TABLE dim_store (
    store_key           SMALLSERIAL  PRIMARY KEY,
    store_code          VARCHAR(20)  NOT NULL UNIQUE,
    store_name          VARCHAR(120) NOT NULL,
    store_type          VARCHAR(40)  NOT NULL,             -- Mall, High Street, Flagship
    city                VARCHAR(80)  NOT NULL,
    region              VARCHAR(80)  NOT NULL,
    country             VARCHAR(80)  NOT NULL DEFAULT 'Pakistan',
    opening_date        DATE         NOT NULL,
    manager_name        VARCHAR(100),
    floor_area_sqft     INTEGER
);

-- -----------------------------------------------------------------------------
-- Table: dim_customer
-- Grain: One row per registered customer (with SCD Type 2 current_flag support).
-- Purpose: Synthetic customer profiles with demographics, loyalty tier, and
--          privacy-masked contact fields (email_hash, phone_hash).
--          Supports 100,000 synthetic customers.
-- -----------------------------------------------------------------------------
CREATE TABLE dim_customer (
    customer_key        BIGSERIAL    PRIMARY KEY,
    customer_code       VARCHAR(30)  NOT NULL UNIQUE,
    full_name           VARCHAR(120) NOT NULL,
    gender              VARCHAR(20),
    age_band            VARCHAR(20),
    city                VARCHAR(80),
    region              VARCHAR(80),
    loyalty_tier        VARCHAR(30),
    registration_date   DATE         NOT NULL,
    email_hash          VARCHAR(80),                       -- Privacy-masked; never expose raw
    phone_hash          VARCHAR(80),                       -- Privacy-masked; never expose raw
    current_flag        BOOLEAN      NOT NULL DEFAULT TRUE
);

-- -----------------------------------------------------------------------------
-- Table: dim_promotion
-- Grain: One row per promotion campaign.
-- Purpose: Tracks 50 promotion campaigns with type, channel, discount percent,
--          and validity dates. Used for promotion-impact analysis.
-- -----------------------------------------------------------------------------
CREATE TABLE dim_promotion (
    promotion_key       SERIAL       PRIMARY KEY,
    promotion_code      VARCHAR(30)  NOT NULL UNIQUE,
    promotion_name      VARCHAR(120) NOT NULL,
    promotion_type      VARCHAR(40)  NOT NULL,             -- Seasonal, Clearance, etc.
    channel             VARCHAR(40)  NOT NULL,             -- Store, Web, App, Omni-channel
    discount_percent    NUMERIC(5,2) NOT NULL,
    start_date          DATE         NOT NULL,
    end_date            DATE         NOT NULL
);

-- -----------------------------------------------------------------------------
-- Table: dim_payment_method
-- Grain: One row per payment method type.
-- Purpose: Classifies payment instruments (cash, card, wallet, bank transfer,
--          BNPL). Supports payment-mix analytics.
-- -----------------------------------------------------------------------------
CREATE TABLE dim_payment_method (
    payment_method_key  SMALLSERIAL  PRIMARY KEY,
    payment_method_code VARCHAR(20)  NOT NULL UNIQUE,
    payment_method_name VARCHAR(60)  NOT NULL,
    payment_provider    VARCHAR(80),
    is_digital          BOOLEAN      NOT NULL
);


-- =============================================================================
-- === SECTION: FACT TABLES ===
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Table: fact_sales_line
-- Grain: One row per product line sold in one order at one store to one customer
--        on one date/time. This is the primary 2.5M-row atomic transaction fact.
-- Purpose: Core sales analytics — revenue, profit, discount, quantity analysis.
--          Links to all 6 dimensions for full drill-down capability.
-- -----------------------------------------------------------------------------
CREATE TABLE fact_sales_line (
    sales_line_id           BIGSERIAL    PRIMARY KEY,
    order_id                BIGINT       NOT NULL,
    order_line_number       SMALLINT     NOT NULL,
    date_key                INTEGER      NOT NULL  REFERENCES dim_date(date_key),
    product_key             BIGINT       NOT NULL  REFERENCES dim_product(product_key),
    store_key               SMALLINT     NOT NULL  REFERENCES dim_store(store_key),
    customer_key            BIGINT       NOT NULL  REFERENCES dim_customer(customer_key),
    promotion_key           INTEGER               REFERENCES dim_promotion(promotion_key),  -- NULL = no promo
    payment_method_key      SMALLINT     NOT NULL  REFERENCES dim_payment_method(payment_method_key),
    order_timestamp         TIMESTAMP    NOT NULL,
    quantity_sold           INTEGER      NOT NULL  CHECK (quantity_sold > 0),
    unit_price              NUMERIC(12,2) NOT NULL,
    gross_sales_amount      NUMERIC(14,2) NOT NULL,
    discount_amount         NUMERIC(14,2) NOT NULL DEFAULT 0,
    net_sales_amount        NUMERIC(14,2) NOT NULL,
    cost_amount             NUMERIC(14,2) NOT NULL,
    profit_amount           NUMERIC(14,2) NOT NULL,
    tax_amount              NUMERIC(14,2) NOT NULL DEFAULT 0,
    load_batch_id           INTEGER      NOT NULL DEFAULT 1,
    created_at              TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(order_id, order_line_number)
);

-- -----------------------------------------------------------------------------
-- Table: fact_inventory_daily_snapshot
-- Grain: One row per product per store per day (periodic snapshot).
-- Purpose: Tracks daily stock movement — opening stock, received, sold, closing.
--          Used for stockout analysis and inventory replenishment questions.
--          Full scale: 10,000 products x 10 stores x 1,096 days = 109M rows.
--          Demo mode: Top 1,000 products only to keep size manageable.
-- -----------------------------------------------------------------------------
CREATE TABLE fact_inventory_daily_snapshot (
    inventory_snapshot_id   BIGSERIAL    PRIMARY KEY,
    date_key                INTEGER      NOT NULL  REFERENCES dim_date(date_key),
    product_key             BIGINT       NOT NULL  REFERENCES dim_product(product_key),
    store_key               SMALLINT     NOT NULL  REFERENCES dim_store(store_key),
    opening_stock_qty       INTEGER      NOT NULL,
    received_qty            INTEGER      NOT NULL  DEFAULT 0,
    sold_qty                INTEGER      NOT NULL  DEFAULT 0,
    closing_stock_qty       INTEGER      NOT NULL,
    stockout_flag           BOOLEAN      NOT NULL,
    UNIQUE(date_key, product_key, store_key)
);

-- -----------------------------------------------------------------------------
-- Table: fact_returns
-- Grain: One row per returned product line (references original sales line).
-- Purpose: Tracks product returns for return-rate analysis. Approximately 1%
--          of sales lines result in a return row.
-- -----------------------------------------------------------------------------
CREATE TABLE fact_returns (
    return_id               BIGSERIAL    PRIMARY KEY,
    original_sales_line_id  BIGINT                REFERENCES fact_sales_line(sales_line_id),
    date_key                INTEGER      NOT NULL  REFERENCES dim_date(date_key),
    product_key             BIGINT       NOT NULL  REFERENCES dim_product(product_key),
    store_key               SMALLINT     NOT NULL  REFERENCES dim_store(store_key),
    customer_key            BIGINT       NOT NULL  REFERENCES dim_customer(customer_key),
    returned_quantity       INTEGER      NOT NULL  CHECK (returned_quantity > 0),
    refund_amount           NUMERIC(14,2) NOT NULL,
    return_reason           VARCHAR(100) NOT NULL
);


-- =============================================================================
-- === SECTION: INDEXES ===
-- Indexing strategy optimized for analytical (OLAP) workloads.
-- Foreign key indexes on fact_sales_line enable fast dimension joins.
-- Composite indexes support common GROUP BY patterns.
-- =============================================================================

-- fact_sales_line: foreign key indexes for fast dimension joins
CREATE INDEX idx_fact_sales_date        ON fact_sales_line(date_key);
CREATE INDEX idx_fact_sales_product     ON fact_sales_line(product_key);
CREATE INDEX idx_fact_sales_store       ON fact_sales_line(store_key);
CREATE INDEX idx_fact_sales_customer    ON fact_sales_line(customer_key);
CREATE INDEX idx_fact_sales_promo       ON fact_sales_line(promotion_key);
CREATE INDEX idx_fact_sales_payment     ON fact_sales_line(payment_method_key);

-- fact_sales_line: timestamp index for time-series and date-range queries
CREATE INDEX idx_fact_sales_order_ts    ON fact_sales_line(order_timestamp);

-- dim_product: composite index for category/subcategory GROUP BY queries
CREATE INDEX idx_product_category_subcategory ON dim_product(category_name, subcategory_name);

-- dim_store: composite index for region/city GROUP BY queries
CREATE INDEX idx_store_region_city      ON dim_store(region, city);

-- dim_customer: composite index for region/city customer segmentation
CREATE INDEX idx_customer_region_city   ON dim_customer(region, city);

-- fact_inventory_daily_snapshot: composite index for daily inventory lookups
CREATE INDEX idx_inventory_date_store_product ON fact_inventory_daily_snapshot(date_key, store_key, product_key);

-- fact_returns: composite index for return-rate analysis by date and product
CREATE INDEX idx_returns_date_product   ON fact_returns(date_key, product_key);

-- =============================================================================
-- Optional future extension: Range-partition fact_sales_line by year/month
-- using order_timestamp or date_key for very large scale (2.5M+ rows).
-- Example: PARTITION BY RANGE (date_key)
-- =============================================================================
