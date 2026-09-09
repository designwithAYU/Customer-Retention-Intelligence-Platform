-- ===========================================================================
-- 06_cohort_analysis.sql -- RETENTION & COHORT ANALYSIS (Q35-Q39)
-- Cohort = signup month. Retention at Mn = customer's subscription was still
-- Active (i.e. not yet cancelled) n months after their cohort's signup month.
-- ===========================================================================

-- Q35. Overall monthly retention (fraction of customers signed up in month M
--      who were still active as of the most recent full month)
WITH first_sub AS (
    SELECT customer_id, MIN(start_date) AS signup_date FROM subscriptions GROUP BY customer_id
),
latest_sub AS (
    SELECT * FROM (SELECT s.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY start_date DESC) rn FROM subscriptions s) WHERE rn=1
)
SELECT strftime('%Y-%m', fs.signup_date) AS cohort_month,
       COUNT(*) AS cohort_size,
       SUM(CASE WHEN ls.subscription_status = 'Active' THEN 1 ELSE 0 END) AS still_active,
       ROUND(100.0*SUM(CASE WHEN ls.subscription_status='Active' THEN 1 ELSE 0 END)/COUNT(*), 2) AS retention_rate_pct
FROM first_sub fs
JOIN latest_sub ls ON ls.customer_id = fs.customer_id
GROUP BY cohort_month
ORDER BY cohort_month;

-- Q36. Cohort retention table at M0/M1/M2/M3/M6/M12
WITH first_sub AS (
    SELECT customer_id, MIN(start_date) AS cohort_date FROM subscriptions GROUP BY customer_id
),
cust_cancel AS (
    -- earliest cancellation date for each customer's original subscription lineage (NULL if never cancelled)
    SELECT customer_id, MIN(CASE WHEN subscription_status='Cancelled' THEN cancellation_date END) AS churn_date
    FROM subscriptions GROUP BY customer_id
),
base AS (
    SELECT fs.customer_id, strftime('%Y-%m', fs.cohort_date) AS cohort_month, fs.cohort_date, cc.churn_date
    FROM first_sub fs LEFT JOIN cust_cancel cc ON cc.customer_id = fs.customer_id
)
SELECT
    cohort_month,
    COUNT(*) AS cohort_size,
    -- retained if churn_date is NULL (never churned) OR churn_date is at/after the milestone date
    ROUND(100.0*SUM(CASE WHEN churn_date IS NULL OR julianday(churn_date) >= julianday(cohort_date) THEN 1 ELSE 0 END)/COUNT(*),1) AS m0_pct,
    ROUND(100.0*SUM(CASE WHEN churn_date IS NULL OR julianday(churn_date) >= julianday(cohort_date)+30 THEN 1 ELSE 0 END)/COUNT(*),1) AS m1_pct,
    ROUND(100.0*SUM(CASE WHEN churn_date IS NULL OR julianday(churn_date) >= julianday(cohort_date)+60 THEN 1 ELSE 0 END)/COUNT(*),1) AS m2_pct,
    ROUND(100.0*SUM(CASE WHEN churn_date IS NULL OR julianday(churn_date) >= julianday(cohort_date)+90 THEN 1 ELSE 0 END)/COUNT(*),1) AS m3_pct,
    ROUND(100.0*SUM(CASE WHEN churn_date IS NULL OR julianday(churn_date) >= julianday(cohort_date)+180 THEN 1 ELSE 0 END)/COUNT(*),1) AS m6_pct,
    ROUND(100.0*SUM(CASE WHEN churn_date IS NULL OR julianday(churn_date) >= julianday(cohort_date)+365 THEN 1 ELSE 0 END)/COUNT(*),1) AS m12_pct
FROM base
GROUP BY cohort_month
ORDER BY cohort_month;

-- Q37. Customer lifetime value (CLV) proxy: total historical revenue per customer, averaged
WITH revenue AS (
    SELECT customer_id, SUM(amount) AS total_revenue
    FROM transactions WHERE transaction_type='Subscription Charge' AND payment_status='Success'
    GROUP BY customer_id
)
SELECT ROUND(AVG(total_revenue), 2) AS avg_clv, ROUND(MIN(total_revenue),2) AS min_clv,
       ROUND(MAX(total_revenue),2) AS max_clv
FROM revenue;

-- Q38. Repeat subscription rate (customers with more than one subscription record)
WITH sub_counts AS (SELECT customer_id, COUNT(*) AS n_subs FROM subscriptions GROUP BY customer_id)
SELECT
    COUNT(*) AS total_customers,
    SUM(CASE WHEN n_subs > 1 THEN 1 ELSE 0 END) AS repeat_customers,
    ROUND(100.0*SUM(CASE WHEN n_subs > 1 THEN 1 ELSE 0 END)/COUNT(*), 2) AS repeat_subscription_rate_pct
FROM sub_counts;

-- Q39. Average customer tenure (days), split by current status
WITH latest_sub AS (
    SELECT * FROM (SELECT s.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY start_date DESC) rn FROM subscriptions s) WHERE rn=1
)
SELECT subscription_status,
       ROUND(AVG(julianday(COALESCE(end_date, '2025-09-01')) - julianday(start_date)), 1) AS avg_tenure_days
FROM latest_sub
GROUP BY subscription_status;
