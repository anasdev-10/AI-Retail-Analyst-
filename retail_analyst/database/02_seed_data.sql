-- =============================================================================
-- FILE: 02_seed_data.sql
-- PURPOSE: Populates all dimension and fact tables with realistic synthetic data
--          for the retail_dw warehouse. Uses set-based PostgreSQL generation
--          (generate_series, LATERAL, CTEs) for efficiency.
--
-- PRODUCTION MODE: fact_sales_line uses 2,500,000 rows (final submission).
--   To run in dev mode, change 2500000 to 10000 in Section 7.
--
-- RUN ORDER: Must be executed AFTER 01_schema.sql
-- USAGE: psql -U postgres -d retail_dw_db -f 02_seed_data.sql
-- EXPECTED COUNTS:
--   dim_date             → 1,096 rows (2024-01-01 to 2026-12-31)
--   dim_store            → 10 rows
--   dim_payment_method   → 5 rows
--   dim_promotion        → 50 rows
--   dim_customer         → 100,000 rows
--   dim_product          → 10,000 rows (10 categories x 10 subcategories x 100 products)
--   fact_sales_line      → 2,500,000 rows (production) / 10,000 (dev)
--   fact_returns         → ~25,000 rows (1% of sales lines)
--   fact_inventory_daily_snapshot → 1,000 products x 10 stores x 1,096 days = ~10.96M rows
-- =============================================================================

SET search_path TO retail_dw;


-- =============================================================================
-- === SECTION 1: dim_date — Calendar dimension 2024-01-01 to 2026-12-31 ===
-- Generates 1,096 rows using generate_series with a 1-day interval.
-- Fiscal year starts July 1 (so July 2024 = FY2025).
-- Fiscal quarter mapping: Q1=Jul-Sep, Q2=Oct-Dec, Q3=Jan-Mar, Q4=Apr-Jun.
-- =============================================================================

INSERT INTO dim_date (
    date_key,
    full_date,
    day_of_week,
    day_name,
    day_of_month,
    week_of_year,
    month_number,
    month_name,
    quarter_number,
    year_number,
    is_weekend,
    fiscal_year,
    fiscal_quarter
)
SELECT
    TO_CHAR(d::date, 'YYYYMMDD')::int                           AS date_key,
    d::date                                                      AS full_date,
    EXTRACT(ISODOW FROM d)::smallint                             AS day_of_week,       -- 1=Mon, 7=Sun
    TRIM(TO_CHAR(d, 'Day'))                                      AS day_name,
    EXTRACT(DAY FROM d)::smallint                                AS day_of_month,
    EXTRACT(WEEK FROM d)::smallint                               AS week_of_year,
    EXTRACT(MONTH FROM d)::smallint                              AS month_number,
    TRIM(TO_CHAR(d, 'Month'))                                    AS month_name,
    EXTRACT(QUARTER FROM d)::smallint                            AS quarter_number,
    EXTRACT(YEAR FROM d)::smallint                               AS year_number,
    CASE WHEN EXTRACT(ISODOW FROM d) IN (6,7) THEN TRUE
         ELSE FALSE END                                          AS is_weekend,
    -- Fiscal year: if month >= July, fiscal year = calendar year + 1
    CASE WHEN EXTRACT(MONTH FROM d) >= 7
         THEN EXTRACT(YEAR FROM d)::smallint + 1
         ELSE EXTRACT(YEAR FROM d)::smallint END                 AS fiscal_year,
    -- Fiscal quarter: shift months so July=month 1 of fiscal year
    -- Formula: ((month + 5) % 12) / 3 + 1
    (((EXTRACT(MONTH FROM d)::int + 5) % 12) / 3 + 1)::smallint AS fiscal_quarter
FROM generate_series(DATE '2024-01-01', DATE '2026-12-31', INTERVAL '1 day') d;


-- =============================================================================
-- === SECTION 2: dim_store — 10 stores across Pakistan ===
-- Exact city names, regions, store types, and manager names as per assignment.
-- =============================================================================

INSERT INTO dim_store (store_code, store_name, store_type, city, region, opening_date, manager_name, floor_area_sqft)
VALUES
    ('STR-001', 'Lahore Emporium',      'Mall',        'Lahore',     'Punjab',      '2021-03-15', 'Ayesha Khan',   25000),
    ('STR-002', 'Karachi Clifton',      'High Street', 'Karachi',    'Sindh',       '2020-08-20', 'Bilal Ahmed',   22000),
    ('STR-003', 'Islamabad Blue Area',  'Flagship',    'Islamabad',  'Capital',     '2019-11-05', 'Sara Malik',    30000),
    ('STR-004', 'Peshawar Saddar',      'High Street', 'Peshawar',   'KPK',         '2022-02-01', 'Hamza Ali',     18000),
    ('STR-005', 'Quetta Cantt',         'High Street', 'Quetta',     'Balochistan', '2022-07-10', 'Zara Shah',     16000),
    ('STR-006', 'Faisalabad D-Ground',  'Mall',        'Faisalabad', 'Punjab',      '2021-12-12', 'Usman Raza',    21000),
    ('STR-007', 'Multan Gulgasht',      'High Street', 'Multan',     'Punjab',      '2023-01-20', 'Hina Noor',     17000),
    ('STR-008', 'Hyderabad Latifabad',  'High Street', 'Hyderabad',  'Sindh',       '2023-05-25', 'Kashif Memon',  16500),
    ('STR-009', 'Rawalpindi Saddar',    'Mall',        'Rawalpindi', 'Punjab',      '2020-04-18', 'Nida Farooq',   23000),
    ('STR-010', 'Sialkot Cantt',        'High Street', 'Sialkot',    'Punjab',      '2024-01-10', 'Danish Butt',   15000);


-- =============================================================================
-- === SECTION 3: dim_payment_method — 5 payment instrument types ===
-- =============================================================================

INSERT INTO dim_payment_method (payment_method_code, payment_method_name, payment_provider, is_digital)
VALUES
    ('CASH',   'Cash',                  'In-store cash',          FALSE),
    ('CARD',   'Debit/Credit Card',     'Bank POS',               TRUE),
    ('WALLET', 'Mobile Wallet',         'JazzCash/EasyPaisa demo', TRUE),
    ('BANK',   'Bank Transfer',         'Online banking',          TRUE),
    ('BNPL',   'Buy Now Pay Later',     'BNPL demo provider',      TRUE);


-- =============================================================================
-- === SECTION 4: dim_promotion — 50 promotion campaigns ===
-- Generated using generate_series with cyclic arrays for type, channel, discount.
-- Dates spread across 900 days with staggered start dates.
-- =============================================================================

INSERT INTO dim_promotion (promotion_code, promotion_name, promotion_type, channel, discount_percent, start_date, end_date)
SELECT
    'PROMO-' || LPAD(gs::text, 3, '0')                                             AS promotion_code,
    'Campaign ' || gs                                                               AS promotion_name,
    (ARRAY['Seasonal','Clearance','Loyalty','Flash Sale','Bundle'])[1 + (gs % 5)]  AS promotion_type,
    (ARRAY['Store','Web','App','Omni-channel'])[1 + (gs % 4)]                      AS channel,
    (ARRAY[5,10,15,20,25])[1 + (gs % 5)]::numeric                                  AS discount_percent,
    DATE '2024-01-01' + ((gs * 17) % 900)                                          AS start_date,
    DATE '2024-01-01' + ((gs * 17) % 900) + 21                                     AS end_date
FROM generate_series(1, 50) gs;


-- =============================================================================
-- === SECTION 5: dim_customer — 100,000 synthetic customer profiles ===
-- Uses generate_series to create realistic demographics.
-- email_hash and phone_hash are MD5-hashed (privacy-masked) fields.
-- =============================================================================

INSERT INTO dim_customer (
    customer_code, full_name, gender, age_band, city, region,
    loyalty_tier, registration_date, email_hash, phone_hash
)
SELECT
    'CUST-' || LPAD(gs::text, 7, '0')                                              AS customer_code,
    'Customer ' || gs                                                               AS full_name,
    (ARRAY['Male','Female','Other/Unknown'])[1 + (gs % 3)]                         AS gender,
    (ARRAY['18-24','25-34','35-44','45-54','55+'])[1 + (gs % 5)]                   AS age_band,
    (ARRAY['Lahore','Karachi','Islamabad','Peshawar','Quetta',
           'Faisalabad','Multan','Hyderabad','Rawalpindi','Sialkot'])[1 + (gs % 10)] AS city,
    (ARRAY['Punjab','Sindh','Capital','KPK','Balochistan'])[1 + (gs % 5)]          AS region,
    (ARRAY['Bronze','Silver','Gold','Platinum'])[1 + (gs % 4)]                     AS loyalty_tier,
    DATE '2021-01-01' + (gs % 1400)                                                AS registration_date,
    md5('customer-email-' || gs)                                                   AS email_hash,
    md5('customer-phone-' || gs)                                                   AS phone_hash
FROM generate_series(1, 100000) gs;


-- =============================================================================
-- === SECTION 6: dim_product — 10 categories x 10 subcategories x 100 products ===
-- Total: 10,000 products using CROSS JOIN CTE pattern.
-- Uses EXACT subcategory names from Assignment Section 4.2 (all 100 names).
-- =============================================================================

WITH subcategory_map(category_name, sub_no, subcategory_name) AS (
    VALUES
        -- Electronics (10 subcategories)
        ('Electronics',        1,  'Laptops'),
        ('Electronics',        2,  'Smartphones'),
        ('Electronics',        3,  'Tablets'),
        ('Electronics',        4,  'Cameras'),
        ('Electronics',        5,  'Headphones'),
        ('Electronics',        6,  'Smart Watches'),
        ('Electronics',        7,  'Networking'),
        ('Electronics',        8,  'Gaming Consoles'),
        ('Electronics',        9,  'Printers'),
        ('Electronics',        10, 'Storage Devices'),
        -- Home & Kitchen (10 subcategories)
        ('Home & Kitchen',     1,  'Cookware'),
        ('Home & Kitchen',     2,  'Appliances'),
        ('Home & Kitchen',     3,  'Furniture'),
        ('Home & Kitchen',     4,  'Bedding'),
        ('Home & Kitchen',     5,  'Lighting'),
        ('Home & Kitchen',     6,  'Decor'),
        ('Home & Kitchen',     7,  'Cleaning'),
        ('Home & Kitchen',     8,  'Kitchen Tools'),
        ('Home & Kitchen',     9,  'Bathroom'),
        ('Home & Kitchen',     10, 'Garden'),
        -- Fashion (10 subcategories)
        ('Fashion',            1,  'Men Shirts'),
        ('Fashion',            2,  'Men Shoes'),
        ('Fashion',            3,  'Women Dresses'),
        ('Fashion',            4,  'Women Shoes'),
        ('Fashion',            5,  'Kids Wear'),
        ('Fashion',            6,  'Watches'),
        ('Fashion',            7,  'Bags'),
        ('Fashion',            8,  'Jewelry'),
        ('Fashion',            9,  'Winter Wear'),
        ('Fashion',            10, 'Activewear'),
        -- Health & Beauty (10 subcategories)
        ('Health & Beauty',    1,  'Skincare'),
        ('Health & Beauty',    2,  'Haircare'),
        ('Health & Beauty',    3,  'Makeup'),
        ('Health & Beauty',    4,  'Fragrance'),
        ('Health & Beauty',    5,  'Personal Care'),
        ('Health & Beauty',    6,  'Vitamins'),
        ('Health & Beauty',    7,  'Fitness Care'),
        ('Health & Beauty',    8,  'Oral Care'),
        ('Health & Beauty',    9,  'Grooming'),
        ('Health & Beauty',    10, 'Baby Care'),
        -- Sports & Outdoors (10 subcategories)
        ('Sports & Outdoors',  1,  'Cricket'),
        ('Sports & Outdoors',  2,  'Football'),
        ('Sports & Outdoors',  3,  'Gym Equipment'),
        ('Sports & Outdoors',  4,  'Cycling'),
        ('Sports & Outdoors',  5,  'Camping'),
        ('Sports & Outdoors',  6,  'Running'),
        ('Sports & Outdoors',  7,  'Swimming'),
        ('Sports & Outdoors',  8,  'Yoga'),
        ('Sports & Outdoors',  9,  'Hiking'),
        ('Sports & Outdoors',  10, 'Sportswear'),
        -- Books & Stationery (10 subcategories)
        ('Books & Stationery', 1,  'Textbooks'),
        ('Books & Stationery', 2,  'Novels'),
        ('Books & Stationery', 3,  'Reference'),
        ('Books & Stationery', 4,  'Notebooks'),
        ('Books & Stationery', 5,  'Pens'),
        ('Books & Stationery', 6,  'Art Supplies'),
        ('Books & Stationery', 7,  'Office Paper'),
        ('Books & Stationery', 8,  'Exam Prep'),
        ('Books & Stationery', 9,  'Magazines'),
        ('Books & Stationery', 10, 'Educational Toys'),
        -- Toys & Games (10 subcategories)
        ('Toys & Games',       1,  'Board Games'),
        ('Toys & Games',       2,  'Puzzles'),
        ('Toys & Games',       3,  'Action Figures'),
        ('Toys & Games',       4,  'Dolls'),
        ('Toys & Games',       5,  'STEM Toys'),
        ('Toys & Games',       6,  'Outdoor Toys'),
        ('Toys & Games',       7,  'Video Games'),
        ('Toys & Games',       8,  'Infant Toys'),
        ('Toys & Games',       9,  'Building Blocks'),
        ('Toys & Games',       10, 'Remote Control'),
        -- Automotive (10 subcategories)
        ('Automotive',         1,  'Car Care'),
        ('Automotive',         2,  'Motorbike Parts'),
        ('Automotive',         3,  'Tyres'),
        ('Automotive',         4,  'Oils'),
        ('Automotive',         5,  'Accessories'),
        ('Automotive',         6,  'Tools'),
        ('Automotive',         7,  'Batteries'),
        ('Automotive',         8,  'Lights'),
        ('Automotive',         9,  'Interior'),
        ('Automotive',         10, 'Safety'),
        -- Grocery (10 subcategories)
        ('Grocery',            1,  'Rice & Grains'),
        ('Grocery',            2,  'Snacks'),
        ('Grocery',            3,  'Beverages'),
        ('Grocery',            4,  'Dairy'),
        ('Grocery',            5,  'Frozen Foods'),
        ('Grocery',            6,  'Breakfast'),
        ('Grocery',            7,  'Spices'),
        ('Grocery',            8,  'Canned Food'),
        ('Grocery',            9,  'Personal Household'),
        ('Grocery',            10, 'Organic'),
        -- Office & Industrial (10 subcategories)
        ('Office & Industrial', 1,  'Desks'),
        ('Office & Industrial', 2,  'Chairs'),
        ('Office & Industrial', 3,  'Filing'),
        ('Office & Industrial', 4,  'Monitors'),
        ('Office & Industrial', 5,  'Projectors'),
        ('Office & Industrial', 6,  'Cables'),
        ('Office & Industrial', 7,  'Packaging'),
        ('Office & Industrial', 8,  'Safety Gear'),
        ('Office & Industrial', 9,  'Lab Supplies'),
        ('Office & Industrial', 10, 'Industrial Tools')
),
-- Assign a numeric subcategory_id (category_order * 10 + sub_no)
category_order(category_name, cat_order) AS (
    VALUES
        ('Electronics',         1),
        ('Home & Kitchen',      2),
        ('Fashion',             3),
        ('Health & Beauty',     4),
        ('Sports & Outdoors',   5),
        ('Books & Stationery',  6),
        ('Toys & Games',        7),
        ('Automotive',          8),
        ('Grocery',             9),
        ('Office & Industrial', 10)
),
subcategories AS (
    SELECT
        sm.category_name,
        sm.subcategory_name,
        ((co.cat_order - 1) * 10 + sm.sub_no) AS subcategory_id
    FROM subcategory_map sm
    JOIN category_order co ON co.category_name = sm.category_name
),
products AS (
    SELECT
        sc.category_name,
        sc.subcategory_name,
        ((sc.subcategory_id - 1) * 100 + p.product_no) AS product_seq,
        p.product_no
    FROM subcategories sc
    CROSS JOIN generate_series(1, 100) p(product_no)
)
INSERT INTO dim_product (
    product_code, product_name, category_name, subcategory_name,
    brand_name, supplier_name, unit_size, color,
    standard_cost, list_price, launch_date
)
SELECT
    'PROD-' || LPAD(product_seq::text, 6, '0')                                     AS product_code,
    subcategory_name || ' Product ' || LPAD(product_no::text, 3, '0')              AS product_name,
    category_name,
    subcategory_name,
    'Brand ' || (1 + product_seq % 50)                                             AS brand_name,
    'Supplier ' || (1 + product_seq % 150)                                         AS supplier_name,
    (ARRAY['Small','Medium','Large','Pack','Single Unit'])[1 + (product_seq % 5)]  AS unit_size,
    (ARRAY['Black','White','Blue','Red','Green','Silver','Mixed'])[1 + (product_seq % 7)] AS color,
    ROUND((50  + random() * 5000)::numeric, 2)                                     AS standard_cost,
    ROUND((80  + random() * 8000)::numeric, 2)                                     AS list_price,
    DATE '2023-01-01' + (product_seq % 1000)                                       AS launch_date
FROM products;


-- =============================================================================
-- === SECTION 7: fact_sales_line — Atomic sales transaction fact ===
--
-- PRODUCTION MODE: 2,500,000 rows (final submission scale).
-- To run in dev mode, change 2500000 to 10000 for faster testing.
--
-- Pattern: every 3 generate_series rows share one order_id (3 lines per order).
-- Uses LATERAL subquery for correlated random values per row.
-- Joins dim_product and dim_date to get real keys and dates.
-- 35% of sales have a promotion applied (promotion_key != NULL).
-- =============================================================================

-- PRODUCTION MODE: 2.5M rows. Change 2500000 to 10000 for quick dev testing.
INSERT INTO fact_sales_line (
    order_id, order_line_number,
    date_key, product_key, store_key, customer_key,
    promotion_key, payment_method_key,
    order_timestamp,
    quantity_sold, unit_price,
    gross_sales_amount, discount_amount, net_sales_amount,
    cost_amount, profit_amount, tax_amount
)
SELECT
    100000000 + ((gs - 1) / 3)                                                     AS order_id,
    (1 + ((gs - 1) % 3))::smallint                                                 AS order_line_number,
    dd.date_key,
    dp.product_key,
    rand_keys.store_key,
    rand_keys.customer_key,
    pr.promotion_key,
    rand_keys.payment_method_key,
    dd.full_date + make_interval(
        hours => rand_keys.hh,
        mins  => rand_keys.mi,
        secs  => rand_keys.ss
    )                                                                               AS order_timestamp,
    rand_keys.quantity_sold,
    dp.list_price                                                                   AS unit_price,
    ROUND((rand_keys.quantity_sold * dp.list_price)::numeric, 2)                   AS gross_sales_amount,
    ROUND((rand_keys.quantity_sold * dp.list_price
           * COALESCE(pr.discount_percent, 0) / 100)::numeric, 2)                 AS discount_amount,
    ROUND((rand_keys.quantity_sold * dp.list_price
           * (1 - COALESCE(pr.discount_percent, 0) / 100))::numeric, 2)           AS net_sales_amount,
    ROUND((rand_keys.quantity_sold * dp.standard_cost)::numeric, 2)               AS cost_amount,
    ROUND((rand_keys.quantity_sold * dp.list_price
           * (1 - COALESCE(pr.discount_percent, 0) / 100)
           - rand_keys.quantity_sold * dp.standard_cost)::numeric, 2)             AS profit_amount,
    ROUND((rand_keys.quantity_sold * dp.list_price * 0.05)::numeric, 2)           AS tax_amount
FROM generate_series(1, 2500000) gs                                                -- ← Change to 10000 for quick dev testing
JOIN LATERAL (
    SELECT
        (1 + (random() * 9999)::int)::bigint    AS product_key,
        (1 + (random() * 9)::int)::smallint     AS store_key,
        (1 + (random() * 99999)::int)::bigint   AS customer_key,
        (1 + (random() * 4)::int)::smallint     AS payment_method_key,
        (1 + (random() * 4)::int)               AS quantity_sold,
        (random() * 1095)::int                  AS day_offset,
        (random() * 23)::int                    AS hh,
        (random() * 59)::int                    AS mi,
        (random() * 59)::int                    AS ss,
        CASE WHEN random() < 0.35
             THEN (1 + (random() * 49)::int)
             ELSE NULL END                       AS promotion_key
) rand_keys ON TRUE
JOIN dim_product  dp ON dp.product_key  = rand_keys.product_key
JOIN dim_date     dd ON dd.full_date    = DATE '2024-01-01' + rand_keys.day_offset
LEFT JOIN dim_promotion pr ON pr.promotion_key = rand_keys.promotion_key;


-- =============================================================================
-- === SECTION 8: fact_returns — ~1% of sales lines become returns ===
-- Selects every 100th sales_line_id (WHERE sales_line_id % 100 = 0).
-- Return date, product, store, and customer are copied from the original sale.
-- =============================================================================

INSERT INTO fact_returns (
    original_sales_line_id, date_key, product_key, store_key, customer_key,
    returned_quantity, refund_amount, return_reason
)
SELECT
    sales_line_id,
    date_key,
    product_key,
    store_key,
    customer_key,
    1                                                                               AS returned_quantity,
    LEAST(net_sales_amount, unit_price)                                            AS refund_amount,
    (ARRAY['Damaged','Wrong item','Late delivery','Changed mind','Quality issue'])
        [1 + (sales_line_id % 5)]                                                  AS return_reason
FROM fact_sales_line
WHERE sales_line_id % 100 = 0;


-- =============================================================================
-- === SECTION 9: fact_inventory_daily_snapshot — Top 1,000 products sample ===
-- Full scale (10,000 products x 10 stores x 1,096 days = 109.6M rows) is too
-- large for most laptops. This script uses top 1,000 products only.
-- Stockout probability set to 3% (realistic for retail inventory).
-- =============================================================================

INSERT INTO fact_inventory_daily_snapshot (
    date_key, product_key, store_key,
    opening_stock_qty, received_qty, sold_qty,
    closing_stock_qty, stockout_flag
)
SELECT
    dd.date_key,
    dp.product_key,
    ds.store_key,
    100 + (random() * 200)::int                                                    AS opening_stock_qty,
    (random() * 50)::int                                                           AS received_qty,
    (random() * 30)::int                                                           AS sold_qty,
    GREATEST(0,
        100 + (random() * 200)::int
            + (random() * 50)::int
            - (random() * 30)::int
    )                                                                              AS closing_stock_qty,
    CASE WHEN random() < 0.03 THEN TRUE ELSE FALSE END                            AS stockout_flag
FROM dim_date dd
CROSS JOIN (
    SELECT product_key FROM dim_product ORDER BY product_key LIMIT 1000
) dp
CROSS JOIN dim_store ds;
