-- =============================================================================
-- FILE: fix_gaps.sql
-- PURPOSE: Targeted fix for two gaps identified in Phase 1:
--   GAP 1: dim_product had generic subcategory names (e.g., "Automotive Subcategory 01")
--           Fixed to: exact assignment names (e.g., "Car Care", "Laptops", "Cricket")
--   GAP 2: fact_sales_line had 10,000 rows (dev mode)
--           Fixed to: 2,500,000 rows (production / assignment requirement)
--
-- WHAT IS PRESERVED (not touched):
--   dim_date, dim_store, dim_payment_method, dim_promotion, dim_customer
--
-- WHAT IS TRUNCATED AND RE-INSERTED:
--   dim_product (10,000 rows with correct subcategory names)
--   fact_sales_line (2,500,000 rows)
--   fact_returns (~25,000 rows = 1% of 2.5M)
--   fact_inventory_daily_snapshot (~10.96M rows)
--
-- ESTIMATED RUN TIME: 20-40 minutes (2.5M fact rows is the slow part)
-- USAGE: psql -U postgres -d retail_dw_db -f retail_analyst/database/fix_gaps.sql
-- =============================================================================

SET search_path TO retail_dw;

-- =============================================================================
-- === STEP 1: TRUNCATE DEPENDENT TABLES (in FK-safe order) ===
-- fact_returns and fact_inventory depend on fact_sales_line and dim_product.
-- fact_sales_line depends on dim_product.
-- We must truncate in reverse dependency order.
-- =============================================================================

TRUNCATE TABLE fact_returns                 RESTART IDENTITY CASCADE;
TRUNCATE TABLE fact_inventory_daily_snapshot RESTART IDENTITY CASCADE;
TRUNCATE TABLE fact_sales_line              RESTART IDENTITY CASCADE;
TRUNCATE TABLE dim_product                  RESTART IDENTITY CASCADE;


-- =============================================================================
-- === STEP 2: RE-INSERT dim_product WITH EXACT SUBCATEGORY NAMES ===
-- All 100 subcategory names exactly as listed in Assignment Section 4.2.
-- 10 categories × 10 subcategories × 100 products = 10,000 total products.
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
-- === STEP 3: RE-INSERT fact_sales_line WITH 2,500,000 ROWS ===
-- PRODUCTION SCALE. This is the main 2.5M-row requirement from the assignment.
-- Estimated time: 15-30 minutes depending on machine speed.
-- =============================================================================

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
FROM generate_series(1, 2500000) gs
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
-- === STEP 4: RE-INSERT fact_returns (~1% = ~25,000 rows) ===
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
-- === STEP 5: RE-INSERT fact_inventory_daily_snapshot (top 1,000 products) ===
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


-- =============================================================================
-- === STEP 6: VERIFY FINAL ROW COUNTS ===
-- =============================================================================

SELECT 'dim_product'                   AS table_name, COUNT(*) AS row_count FROM dim_product
UNION ALL
SELECT 'fact_sales_line',                              COUNT(*) FROM fact_sales_line
UNION ALL
SELECT 'fact_returns',                                 COUNT(*) FROM fact_returns
UNION ALL
SELECT 'fact_inventory_daily_snapshot',                COUNT(*) FROM fact_inventory_daily_snapshot
ORDER BY table_name;
