-- ===========================================================================
-- 02_data_quality.sql
-- Post-load validation queries against the CLEANED tables.
-- These queries confirm that the cleaning stage (src/clean_data.py) produced
-- data that satisfies the project's integrity expectations.
-- ===========================================================================

-- Q1. Row counts per table
SELECT 'customers' AS table_name, COUNT(*) AS row_count FROM customers
UNION ALL SELECT 'plans', COUNT(*) FROM plans
UNION ALL SELECT 'subscriptions', COUNT(*) FROM subscriptions
UNION ALL SELECT 'transactions', COUNT(*) FROM transactions
UNION ALL SELECT 'customer_activity', COUNT(*) FROM customer_activity
UNION ALL SELECT 'support_tickets', COUNT(*) FROM support_tickets
UNION ALL SELECT 'marketing_campaigns', COUNT(*) FROM marketing_campaigns
UNION ALL SELECT 'customer_campaign_interactions', COUNT(*) FROM customer_campaign_interactions;

-- Q2. Duplicate customer_id check (should be 0 after cleaning)
SELECT customer_id, COUNT(*) AS n
FROM customers
GROUP BY customer_id
HAVING COUNT(*) > 1;

-- Q3. Orphan subscriptions (customer_id not present in customers) -- should be 0
SELECT s.subscription_id
FROM subscriptions s
LEFT JOIN customers c ON c.customer_id = s.customer_id
WHERE c.customer_id IS NULL;

-- Q4. Orphan transactions (subscription_id not present in subscriptions) -- should be 0
SELECT t.transaction_id
FROM transactions t
LEFT JOIN subscriptions s ON s.subscription_id = t.subscription_id
WHERE s.subscription_id IS NULL;

-- Q5. Cancelled subscriptions with no cancellation_date -- should be 0
SELECT subscription_id
FROM subscriptions
WHERE subscription_status = 'Cancelled' AND cancellation_date IS NULL;

-- Q6. Subscriptions with end_date before start_date -- should be 0
SELECT subscription_id
FROM subscriptions
WHERE end_date IS NOT NULL AND end_date < start_date;

-- Q7. Negative subscription charges that are not refunds -- should be 0
SELECT transaction_id
FROM transactions
WHERE transaction_type = 'Subscription Charge' AND amount < 0 AND payment_status <> 'Refunded';

-- Q8. Ages outside plausible bounds -- should be 0
SELECT customer_id, age FROM customers WHERE age < 13 OR age > 100;

-- Q9. Null-rate audit across key columns
SELECT
    SUM(CASE WHEN gender IS NULL THEN 1 ELSE 0 END)   AS null_gender,
    SUM(CASE WHEN country IS NULL THEN 1 ELSE 0 END)  AS null_country,
    SUM(CASE WHEN age IS NULL THEN 1 ELSE 0 END)      AS null_age
FROM customers;

-- Q10. Distinct categorical values (spot-check standardization worked)
SELECT DISTINCT subscription_status FROM subscriptions ORDER BY 1;
SELECT DISTINCT billing_cycle FROM subscriptions ORDER BY 1;
SELECT DISTINCT issue_type FROM support_tickets ORDER BY 1;
