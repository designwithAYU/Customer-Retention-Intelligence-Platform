-- ===========================================================================
-- 03_customer_analysis.sql -- CUSTOMER ANALYSIS (Q1-Q8)
-- ===========================================================================

-- Q1. Total customers
SELECT COUNT(*) AS total_customers FROM customers;

-- Q2. Active customers (most recent subscription is Active)
WITH latest_sub AS (
    SELECT customer_id, subscription_status,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY start_date DESC) AS rn
    FROM subscriptions
)
SELECT COUNT(*) AS active_customers
FROM latest_sub
WHERE rn = 1 AND subscription_status = 'Active';

-- Q3. Churned customers (most recent subscription is Cancelled)
WITH latest_sub AS (
    SELECT customer_id, subscription_status,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY start_date DESC) AS rn
    FROM subscriptions
)
SELECT COUNT(*) AS churned_customers
FROM latest_sub
WHERE rn = 1 AND subscription_status = 'Cancelled';

-- Q4. New customers by signup month
SELECT strftime('%Y-%m', signup_date) AS signup_month, COUNT(*) AS new_customers
FROM customers
GROUP BY 1
ORDER BY 1;

-- Q5. Customers by region
SELECT region, COUNT(*) AS customers, ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM customers), 2) AS pct_of_total
FROM customers
GROUP BY region
ORDER BY customers DESC;

-- Q6. Customers by acquisition channel
SELECT acquisition_channel, COUNT(*) AS customers,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM customers), 2) AS pct_of_total
FROM customers
GROUP BY acquisition_channel
ORDER BY customers DESC;

-- Q7. Customers by current plan (most recent subscription)
WITH latest_sub AS (
    SELECT customer_id, plan_id,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY start_date DESC) AS rn
    FROM subscriptions
)
SELECT p.plan_name, COUNT(*) AS customers
FROM latest_sub ls
JOIN plans p ON p.plan_id = ls.plan_id
WHERE ls.rn = 1
GROUP BY p.plan_name
ORDER BY customers DESC;

-- Q8. Customers by tenure bucket (months since signup, as of the data cutoff)
SELECT tenure_bucket, COUNT(*) AS customers
FROM (
    SELECT customer_id,
        CASE
            WHEN tenure_months < 3 THEN '1 - 0-2 months'
            WHEN tenure_months < 6 THEN '2 - 3-5 months'
            WHEN tenure_months < 12 THEN '3 - 6-11 months'
            WHEN tenure_months < 18 THEN '4 - 12-17 months'
            ELSE '5 - 18+ months'
        END AS tenure_bucket
    FROM (
        SELECT customer_id,
               CAST((julianday('2025-09-01') - julianday(signup_date)) / 30 AS INTEGER) AS tenure_months
        FROM customers
    ) t
) buckets
GROUP BY tenure_bucket
ORDER BY tenure_bucket;
