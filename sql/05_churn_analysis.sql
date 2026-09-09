-- ===========================================================================
-- 05_churn_analysis.sql -- CHURN ANALYSIS (Q18-Q28) + CUSTOMER BEHAVIOR (Q29-Q34)
-- Churn definition: a subscription is churned when subscription_status =
-- 'Cancelled'. A customer is treated as churned when their most recent
-- subscription record is Cancelled (see reports/methodology.md, Step 9).
-- ===========================================================================

-- Q18. Overall churn rate (subscription-level, across all subscriptions ever created)
SELECT ROUND(100.0 * SUM(CASE WHEN subscription_status='Cancelled' THEN 1 ELSE 0 END) / COUNT(*), 2) AS overall_churn_rate_pct
FROM subscriptions;

-- Q19. Monthly churn rate (cancellations in month / active subscriptions at start of month, approximated)
WITH cancels AS (
    SELECT strftime('%Y-%m', cancellation_date) AS month, COUNT(*) AS cancellations
    FROM subscriptions
    WHERE subscription_status = 'Cancelled'
    GROUP BY 1
),
active_base AS (
    SELECT strftime('%Y-%m', start_date) AS month, COUNT(*) AS new_active
    FROM subscriptions
    GROUP BY 1
)
SELECT c.month, c.cancellations,
       ROUND(100.0 * c.cancellations / NULLIF((SELECT SUM(new_active) FROM active_base a WHERE a.month <= c.month), 0), 3) AS approx_monthly_churn_rate_pct
FROM cancels c
ORDER BY c.month;

-- Q20. Churn by plan
SELECT p.plan_name,
       COUNT(*) AS total_subs,
       SUM(CASE WHEN s.subscription_status='Cancelled' THEN 1 ELSE 0 END) AS churned,
       ROUND(100.0*SUM(CASE WHEN s.subscription_status='Cancelled' THEN 1 ELSE 0 END)/COUNT(*),2) AS churn_rate_pct
FROM subscriptions s JOIN plans p ON p.plan_id = s.plan_id
GROUP BY p.plan_name ORDER BY churn_rate_pct DESC;

-- Q21. Churn by billing cycle
SELECT billing_cycle,
       COUNT(*) AS total_subs,
       SUM(CASE WHEN subscription_status='Cancelled' THEN 1 ELSE 0 END) AS churned,
       ROUND(100.0*SUM(CASE WHEN subscription_status='Cancelled' THEN 1 ELSE 0 END)/COUNT(*),2) AS churn_rate_pct
FROM subscriptions
GROUP BY billing_cycle ORDER BY churn_rate_pct DESC;

-- Q22. Churn by region
SELECT c.region,
       COUNT(*) AS total_subs,
       SUM(CASE WHEN s.subscription_status='Cancelled' THEN 1 ELSE 0 END) AS churned,
       ROUND(100.0*SUM(CASE WHEN s.subscription_status='Cancelled' THEN 1 ELSE 0 END)/COUNT(*),2) AS churn_rate_pct
FROM subscriptions s JOIN customers c ON c.customer_id = s.customer_id
GROUP BY c.region ORDER BY churn_rate_pct DESC;

-- Q23. Churn by acquisition channel
SELECT c.acquisition_channel,
       COUNT(*) AS total_subs,
       SUM(CASE WHEN s.subscription_status='Cancelled' THEN 1 ELSE 0 END) AS churned,
       ROUND(100.0*SUM(CASE WHEN s.subscription_status='Cancelled' THEN 1 ELSE 0 END)/COUNT(*),2) AS churn_rate_pct
FROM subscriptions s JOIN customers c ON c.customer_id = s.customer_id
GROUP BY c.acquisition_channel ORDER BY churn_rate_pct DESC;

-- Q24. Churn by tenure bucket at time of observation (uses length of subscription)
SELECT
    CASE
        WHEN tenure_days < 90 THEN '1 - 0-3 months'
        WHEN tenure_days < 180 THEN '2 - 3-6 months'
        WHEN tenure_days < 365 THEN '3 - 6-12 months'
        ELSE '4 - 12+ months'
    END AS tenure_bucket,
    COUNT(*) AS total_subs,
    SUM(is_cancelled) AS churned,
    ROUND(100.0*SUM(is_cancelled)/COUNT(*),2) AS churn_rate_pct
FROM (
    SELECT subscription_id,
           CASE WHEN subscription_status='Cancelled' THEN 1 ELSE 0 END AS is_cancelled,
           CAST(julianday(COALESCE(end_date, '2025-09-01')) - julianday(start_date) AS INTEGER) AS tenure_days
    FROM subscriptions
) x
GROUP BY tenure_bucket ORDER BY tenure_bucket;

-- Q25. Churn by age group
SELECT
    CASE WHEN c.age < 25 THEN '1 - Under 25' WHEN c.age < 35 THEN '2 - 25-34'
         WHEN c.age < 45 THEN '3 - 35-44' WHEN c.age < 60 THEN '4 - 45-59'
         ELSE '5 - 60+' END AS age_group,
    COUNT(*) AS total_subs,
    SUM(CASE WHEN s.subscription_status='Cancelled' THEN 1 ELSE 0 END) AS churned,
    ROUND(100.0*SUM(CASE WHEN s.subscription_status='Cancelled' THEN 1 ELSE 0 END)/COUNT(*),2) AS churn_rate_pct
FROM subscriptions s JOIN customers c ON c.customer_id = s.customer_id
GROUP BY age_group ORDER BY age_group;

-- Q26. Churn by engagement level (avg sessions, tercile)
WITH cust_engagement AS (
    SELECT customer_id, AVG(sessions) AS avg_sessions FROM customer_activity GROUP BY customer_id
),
tercile AS (
    SELECT customer_id, avg_sessions, NTILE(3) OVER (ORDER BY avg_sessions) AS eng_tercile FROM cust_engagement
),
latest_sub AS (
    SELECT * FROM (SELECT s.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY start_date DESC) rn FROM subscriptions s) WHERE rn=1
)
SELECT CASE eng_tercile WHEN 1 THEN '1 - Low engagement' WHEN 2 THEN '2 - Medium engagement' ELSE '3 - High engagement' END AS engagement_level,
       COUNT(*) AS customers,
       SUM(CASE WHEN ls.subscription_status='Cancelled' THEN 1 ELSE 0 END) AS churned,
       ROUND(100.0*SUM(CASE WHEN ls.subscription_status='Cancelled' THEN 1 ELSE 0 END)/COUNT(*),2) AS churn_rate_pct
FROM tercile t JOIN latest_sub ls ON ls.customer_id = t.customer_id
GROUP BY engagement_level ORDER BY engagement_level;

-- Q27. Churn by satisfaction score
WITH cust_sat AS (
    SELECT customer_id, AVG(satisfaction_score) AS avg_sat FROM support_tickets GROUP BY customer_id
),
latest_sub AS (
    SELECT * FROM (SELECT s.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY start_date DESC) rn FROM subscriptions s) WHERE rn=1
)
SELECT
    CASE WHEN cs.avg_sat < 2 THEN '1 - Very Low (<2)' WHEN cs.avg_sat < 3 THEN '2 - Low (2-3)'
         WHEN cs.avg_sat < 4 THEN '3 - Medium (3-4)' ELSE '4 - High (4-5)' END AS satisfaction_band,
    COUNT(*) AS customers,
    SUM(CASE WHEN ls.subscription_status='Cancelled' THEN 1 ELSE 0 END) AS churned,
    ROUND(100.0*SUM(CASE WHEN ls.subscription_status='Cancelled' THEN 1 ELSE 0 END)/COUNT(*),2) AS churn_rate_pct
FROM cust_sat cs JOIN latest_sub ls ON ls.customer_id = cs.customer_id
GROUP BY satisfaction_band ORDER BY satisfaction_band;

-- Q28. Churn by support ticket volume
WITH cust_tickets AS (
    SELECT customer_id, COUNT(*) AS n_tickets FROM support_tickets GROUP BY customer_id
),
latest_sub AS (
    SELECT * FROM (SELECT s.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY start_date DESC) rn FROM subscriptions s) WHERE rn=1
)
SELECT
    CASE WHEN ct.n_tickets = 0 THEN '1 - No tickets' WHEN ct.n_tickets <= 2 THEN '2 - 1-2 tickets'
         WHEN ct.n_tickets <= 4 THEN '3 - 3-4 tickets' ELSE '4 - 5+ tickets' END AS ticket_volume_band,
    COUNT(*) AS customers,
    SUM(CASE WHEN ls.subscription_status='Cancelled' THEN 1 ELSE 0 END) AS churned,
    ROUND(100.0*SUM(CASE WHEN ls.subscription_status='Cancelled' THEN 1 ELSE 0 END)/COUNT(*),2) AS churn_rate_pct
FROM latest_sub ls
LEFT JOIN cust_tickets ct ON ct.customer_id = ls.customer_id
GROUP BY ticket_volume_band ORDER BY ticket_volume_band;

-- ===========================================================================
-- CUSTOMER BEHAVIOR (Q29-Q34)
-- ===========================================================================

-- Q29. Average sessions: churned vs active customers
WITH latest_sub AS (
    SELECT * FROM (SELECT s.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY start_date DESC) rn FROM subscriptions s) WHERE rn=1
),
eng AS (SELECT customer_id, AVG(sessions) AS avg_sessions FROM customer_activity GROUP BY customer_id)
SELECT ls.subscription_status, ROUND(AVG(e.avg_sessions), 2) AS avg_sessions_per_customer
FROM latest_sub ls JOIN eng e ON e.customer_id = ls.customer_id
GROUP BY ls.subscription_status;

-- Q30. Average session duration: churned vs active
WITH latest_sub AS (
    SELECT * FROM (SELECT s.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY start_date DESC) rn FROM subscriptions s) WHERE rn=1
),
eng AS (SELECT customer_id, AVG(session_minutes) AS avg_minutes FROM customer_activity GROUP BY customer_id)
SELECT ls.subscription_status, ROUND(AVG(e.avg_minutes), 2) AS avg_session_minutes
FROM latest_sub ls JOIN eng e ON e.customer_id = ls.customer_id
GROUP BY ls.subscription_status;

-- Q31. Feature usage comparison: churned vs active
WITH latest_sub AS (
    SELECT * FROM (SELECT s.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY start_date DESC) rn FROM subscriptions s) WHERE rn=1
),
eng AS (SELECT customer_id, AVG(feature_usage_count) AS avg_feature_usage FROM customer_activity GROUP BY customer_id)
SELECT ls.subscription_status, ROUND(AVG(e.avg_feature_usage), 2) AS avg_feature_usage
FROM latest_sub ls JOIN eng e ON e.customer_id = ls.customer_id
GROUP BY ls.subscription_status;

-- Q32. Support ticket comparison: churned vs active
WITH latest_sub AS (
    SELECT * FROM (SELECT s.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY start_date DESC) rn FROM subscriptions s) WHERE rn=1
),
tix AS (SELECT customer_id, COUNT(*) AS n_tickets, AVG(satisfaction_score) AS avg_sat FROM support_tickets GROUP BY customer_id)
SELECT ls.subscription_status, ROUND(AVG(COALESCE(t.n_tickets,0)), 2) AS avg_tickets, ROUND(AVG(t.avg_sat), 2) AS avg_satisfaction
FROM latest_sub ls LEFT JOIN tix t ON t.customer_id = ls.customer_id
GROUP BY ls.subscription_status;

-- Q33. Customers with declining engagement (last 30 days activity < prior 30-60 days, still Active)
WITH latest_sub AS (
    SELECT * FROM (SELECT s.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY start_date DESC) rn FROM subscriptions s) WHERE rn=1
),
recent AS (
    SELECT customer_id, AVG(sessions) AS recent_avg
    FROM customer_activity WHERE activity_date >= date('2025-08-01') GROUP BY customer_id
),
prior AS (
    SELECT customer_id, AVG(sessions) AS prior_avg
    FROM customer_activity WHERE activity_date >= date('2025-06-01') AND activity_date < date('2025-08-01') GROUP BY customer_id
)
SELECT COUNT(*) AS declining_engagement_customers
FROM latest_sub ls
JOIN recent r ON r.customer_id = ls.customer_id
JOIN prior p ON p.customer_id = ls.customer_id
WHERE ls.subscription_status = 'Active' AND r.recent_avg < 0.6 * p.prior_avg;

-- Q34. HIGH-VALUE customers with declining engagement (top revenue quartile + declining)
WITH latest_sub AS (
    SELECT * FROM (SELECT s.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY start_date DESC) rn FROM subscriptions s) WHERE rn=1
),
revenue AS (
    SELECT customer_id, SUM(amount) AS total_revenue
    FROM transactions WHERE transaction_type='Subscription Charge' AND payment_status='Success'
    GROUP BY customer_id
),
rev_quartile AS (
    SELECT customer_id, total_revenue, NTILE(4) OVER (ORDER BY total_revenue) AS q FROM revenue
),
recent AS (
    SELECT customer_id, AVG(sessions) AS recent_avg
    FROM customer_activity WHERE activity_date >= date('2025-08-01') GROUP BY customer_id
),
prior AS (
    SELECT customer_id, AVG(sessions) AS prior_avg
    FROM customer_activity WHERE activity_date >= date('2025-06-01') AND activity_date < date('2025-08-01') GROUP BY customer_id
)
SELECT COUNT(*) AS high_value_declining_customers, ROUND(SUM(rq.total_revenue),2) AS revenue_represented
FROM latest_sub ls
JOIN rev_quartile rq ON rq.customer_id = ls.customer_id AND rq.q = 4
JOIN recent r ON r.customer_id = ls.customer_id
JOIN prior p ON p.customer_id = ls.customer_id
WHERE ls.subscription_status = 'Active' AND r.recent_avg < 0.6 * p.prior_avg;
