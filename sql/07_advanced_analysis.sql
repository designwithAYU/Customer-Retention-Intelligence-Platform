-- ===========================================================================
-- 07_advanced_analysis.sql -- ADVANCED ANALYSIS (Q40-Q47)
-- ===========================================================================

-- Q40. Top 10% customers by revenue
WITH revenue AS (
    SELECT customer_id, SUM(amount) AS total_revenue
    FROM transactions WHERE transaction_type='Subscription Charge' AND payment_status='Success'
    GROUP BY customer_id
),
ranked AS (
    SELECT customer_id, total_revenue, NTILE(10) OVER (ORDER BY total_revenue DESC) AS decile
    FROM revenue
)
SELECT COUNT(*) AS top_decile_customers, ROUND(SUM(total_revenue),2) AS revenue_from_top_decile,
       ROUND(100.0*SUM(total_revenue)/(SELECT SUM(total_revenue) FROM revenue), 2) AS pct_of_total_revenue
FROM ranked WHERE decile = 1;

-- Q41. High-value customers at risk (top revenue quartile + Active + low satisfaction or unresolved tickets)
WITH latest_sub AS (
    SELECT * FROM (SELECT s.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY start_date DESC) rn FROM subscriptions s) WHERE rn=1
),
revenue AS (
    SELECT customer_id, SUM(amount) AS total_revenue
    FROM transactions WHERE transaction_type='Subscription Charge' AND payment_status='Success'
    GROUP BY customer_id
),
rev_q AS (SELECT customer_id, total_revenue, NTILE(4) OVER (ORDER BY total_revenue) AS q FROM revenue),
support AS (
    SELECT customer_id, AVG(satisfaction_score) AS avg_sat,
           SUM(CASE WHEN ticket_status='Closed - Unresolved' THEN 1 ELSE 0 END) AS unresolved
    FROM support_tickets GROUP BY customer_id
)
SELECT COUNT(*) AS high_value_at_risk_customers, ROUND(SUM(rq.total_revenue),2) AS revenue_at_risk
FROM latest_sub ls
JOIN rev_q rq ON rq.customer_id = ls.customer_id AND rq.q = 4
LEFT JOIN support sp ON sp.customer_id = ls.customer_id
WHERE ls.subscription_status = 'Active'
  AND (COALESCE(sp.avg_sat,5) <= 3 OR COALESCE(sp.unresolved,0) >= 1);

-- Q42. Customers with high support issue volume (top decile of ticket count)
WITH tix AS (SELECT customer_id, COUNT(*) AS n_tickets FROM support_tickets GROUP BY customer_id)
SELECT COUNT(*) AS high_ticket_customers, MIN(n_tickets) AS min_tickets_in_group
FROM (SELECT customer_id, n_tickets, NTILE(10) OVER (ORDER BY n_tickets DESC) AS decile FROM tix) x
WHERE decile = 1;

-- Q43. Customers with high revenue but low engagement (top revenue quartile, bottom engagement tercile)
WITH revenue AS (
    SELECT customer_id, SUM(amount) AS total_revenue
    FROM transactions WHERE transaction_type='Subscription Charge' AND payment_status='Success'
    GROUP BY customer_id
),
rev_q AS (SELECT customer_id, total_revenue, NTILE(4) OVER (ORDER BY total_revenue) AS q FROM revenue),
eng AS (SELECT customer_id, AVG(sessions) AS avg_sessions FROM customer_activity GROUP BY customer_id),
eng_t AS (SELECT customer_id, avg_sessions, NTILE(3) OVER (ORDER BY avg_sessions) AS t FROM eng)
SELECT COUNT(*) AS high_revenue_low_engagement_customers, ROUND(SUM(rq.total_revenue),2) AS revenue_represented
FROM rev_q rq JOIN eng_t et ON et.customer_id = rq.customer_id
WHERE rq.q = 4 AND et.t = 1;

-- Q44. Revenue at risk by plan (Active subscriptions, annualized recurring value)
WITH latest_sub AS (
    SELECT * FROM (SELECT s.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY start_date DESC) rn FROM subscriptions s) WHERE rn=1
),
support AS (
    SELECT customer_id, AVG(satisfaction_score) AS avg_sat FROM support_tickets GROUP BY customer_id
)
SELECT p.plan_name,
       ROUND(SUM(CASE WHEN ls.billing_cycle='Monthly' THEN ls.monthly_price*12 ELSE ls.monthly_price END),2) AS at_risk_revenue
FROM latest_sub ls
JOIN plans p ON p.plan_id = ls.plan_id
LEFT JOIN support sp ON sp.customer_id = ls.customer_id
WHERE ls.subscription_status='Active' AND COALESCE(sp.avg_sat,5) <= 3
GROUP BY p.plan_name ORDER BY at_risk_revenue DESC;

-- Q45. Revenue at risk by region
WITH latest_sub AS (
    SELECT * FROM (SELECT s.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY start_date DESC) rn FROM subscriptions s) WHERE rn=1
),
support AS (SELECT customer_id, AVG(satisfaction_score) AS avg_sat FROM support_tickets GROUP BY customer_id)
SELECT c.region,
       ROUND(SUM(CASE WHEN ls.billing_cycle='Monthly' THEN ls.monthly_price*12 ELSE ls.monthly_price END),2) AS at_risk_revenue
FROM latest_sub ls
JOIN customers c ON c.customer_id = ls.customer_id
LEFT JOIN support sp ON sp.customer_id = ls.customer_id
WHERE ls.subscription_status='Active' AND COALESCE(sp.avg_sat,5) <= 3
GROUP BY c.region ORDER BY at_risk_revenue DESC;

-- Q46. Revenue at risk by acquisition channel
WITH latest_sub AS (
    SELECT * FROM (SELECT s.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY start_date DESC) rn FROM subscriptions s) WHERE rn=1
),
support AS (SELECT customer_id, AVG(satisfaction_score) AS avg_sat FROM support_tickets GROUP BY customer_id)
SELECT c.acquisition_channel,
       ROUND(SUM(CASE WHEN ls.billing_cycle='Monthly' THEN ls.monthly_price*12 ELSE ls.monthly_price END),2) AS at_risk_revenue
FROM latest_sub ls
JOIN customers c ON c.customer_id = ls.customer_id
LEFT JOIN support sp ON sp.customer_id = ls.customer_id
WHERE ls.subscription_status='Active' AND COALESCE(sp.avg_sat,5) <= 3
GROUP BY c.acquisition_channel ORDER BY at_risk_revenue DESC;

-- Q47. Retention priority customers (simple SQL-only proxy combining value + risk signals;
--      the full ML-based retention priority score is computed in src/churn_model.py)
WITH latest_sub AS (
    SELECT * FROM (SELECT s.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY start_date DESC) rn FROM subscriptions s) WHERE rn=1
),
revenue AS (
    SELECT customer_id, SUM(amount) AS total_revenue
    FROM transactions WHERE transaction_type='Subscription Charge' AND payment_status='Success'
    GROUP BY customer_id
),
support AS (
    SELECT customer_id, AVG(satisfaction_score) AS avg_sat,
           SUM(CASE WHEN ticket_status='Closed - Unresolved' THEN 1 ELSE 0 END) AS unresolved
    FROM support_tickets GROUP BY customer_id
)
SELECT ls.customer_id, ROUND(r.total_revenue,2) AS total_revenue,
       ROUND(COALESCE(sp.avg_sat,5),2) AS avg_satisfaction, COALESCE(sp.unresolved,0) AS unresolved_tickets
FROM latest_sub ls
JOIN revenue r ON r.customer_id = ls.customer_id
LEFT JOIN support sp ON sp.customer_id = ls.customer_id
WHERE ls.subscription_status='Active'
ORDER BY (COALESCE(sp.unresolved,0) * 1000 + (5 - COALESCE(sp.avg_sat,5)) * 500 + r.total_revenue / 100.0) DESC
LIMIT 25;
