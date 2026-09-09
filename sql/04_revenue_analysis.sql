-- ===========================================================================
-- 04_revenue_analysis.sql -- REVENUE ANALYSIS (Q9-Q17)
-- Revenue = successful "Subscription Charge" transactions only.
-- ===========================================================================

-- Q9. Total revenue (all-time, successful subscription charges)
SELECT ROUND(SUM(amount), 2) AS total_revenue
FROM transactions
WHERE transaction_type = 'Subscription Charge' AND payment_status = 'Success';

-- Q10. Monthly revenue
SELECT strftime('%Y-%m', transaction_date) AS revenue_month, ROUND(SUM(amount), 2) AS revenue
FROM transactions
WHERE transaction_type = 'Subscription Charge' AND payment_status = 'Success'
GROUP BY 1
ORDER BY 1;

-- Q11. Month-over-month revenue growth %
WITH monthly AS (
    SELECT strftime('%Y-%m', transaction_date) AS revenue_month, SUM(amount) AS revenue
    FROM transactions
    WHERE transaction_type = 'Subscription Charge' AND payment_status = 'Success'
    GROUP BY 1
)
SELECT revenue_month, ROUND(revenue, 2) AS revenue,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY revenue_month)) / LAG(revenue) OVER (ORDER BY revenue_month), 2) AS mom_growth_pct
FROM monthly
ORDER BY revenue_month;

-- Q12. Revenue by plan
SELECT p.plan_name, ROUND(SUM(t.amount), 2) AS revenue,
       ROUND(100.0 * SUM(t.amount) / (SELECT SUM(amount) FROM transactions WHERE transaction_type='Subscription Charge' AND payment_status='Success'), 2) AS pct_of_total
FROM transactions t
JOIN subscriptions s ON s.subscription_id = t.subscription_id
JOIN plans p ON p.plan_id = s.plan_id
WHERE t.transaction_type = 'Subscription Charge' AND t.payment_status = 'Success'
GROUP BY p.plan_name
ORDER BY revenue DESC;

-- Q13. Revenue by region
SELECT c.region, ROUND(SUM(t.amount), 2) AS revenue
FROM transactions t
JOIN customers c ON c.customer_id = t.customer_id
WHERE t.transaction_type = 'Subscription Charge' AND t.payment_status = 'Success'
GROUP BY c.region
ORDER BY revenue DESC;

-- Q14. Revenue by acquisition channel
SELECT c.acquisition_channel, ROUND(SUM(t.amount), 2) AS revenue
FROM transactions t
JOIN customers c ON c.customer_id = t.customer_id
WHERE t.transaction_type = 'Subscription Charge' AND t.payment_status = 'Success'
GROUP BY c.acquisition_channel
ORDER BY revenue DESC;

-- Q15. ARPU (Average Revenue Per User), all-time
SELECT ROUND(
    (SELECT SUM(amount) FROM transactions WHERE transaction_type='Subscription Charge' AND payment_status='Success')
    / (SELECT COUNT(DISTINCT customer_id) FROM customers), 2
) AS arpu_all_time;

-- Q16. Revenue lost from churn (sum of monthly_price for all cancelled subscriptions,
--      annualized to show the recurring revenue impact of cancellations to date)
SELECT ROUND(SUM(
    CASE WHEN billing_cycle = 'Monthly' THEN monthly_price * 12 ELSE monthly_price END
), 2) AS annualized_revenue_lost_to_churn
FROM subscriptions
WHERE subscription_status = 'Cancelled';

-- Q17. Revenue at risk (simple proxy: annualized recurring value of currently Active
--      subscriptions belonging to customers with below-median satisfaction OR
--      unresolved support tickets -- refined further with ML churn probability in Step 18)
WITH latest_sub AS (
    SELECT * FROM (
        SELECT s.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY start_date DESC) AS rn
        FROM subscriptions s
    ) WHERE rn = 1
),
support AS (
    SELECT customer_id, AVG(satisfaction_score) AS avg_satisfaction,
           SUM(CASE WHEN ticket_status='Closed - Unresolved' THEN 1 ELSE 0 END) AS unresolved
    FROM support_tickets GROUP BY customer_id
)
SELECT ROUND(SUM(CASE WHEN ls.billing_cycle='Monthly' THEN ls.monthly_price*12 ELSE ls.monthly_price END), 2) AS naive_revenue_at_risk
FROM latest_sub ls
LEFT JOIN support sp ON sp.customer_id = ls.customer_id
WHERE ls.subscription_status = 'Active'
  AND (COALESCE(sp.avg_satisfaction, 5) <= 2.5 OR COALESCE(sp.unresolved, 0) >= 2);
