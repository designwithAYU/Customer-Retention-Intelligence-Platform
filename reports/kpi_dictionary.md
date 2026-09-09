# KPI Dictionary

**Project:** Customer Retention Intelligence Platform (NovaStream)

Every KPI below includes its definition, formula, a reference SQL
implementation, and its business meaning. These definitions are kept
consistent across SQL (`sql/`), Python (`src/`), and Power BI (`powerbi/dax_measures.md`).

---

## Customer KPIs

### Total Customers
- **Definition:** Count of all unique customers who have ever signed up.
- **Formula:** `COUNT(DISTINCT customer_id)`
- **SQL:** `SELECT COUNT(*) FROM customers;`
- **Business meaning:** The size of the addressable customer base to date.

### Active Customers
- **Definition:** Customers whose most recent subscription record has status `Active`.
- **Formula:** `COUNT(customers WHERE latest subscription_status = 'Active')`
- **SQL:** See `sql/03_customer_analysis.sql`, Q2.
- **Business meaning:** Customers currently generating recurring revenue.

### Churned Customers
- **Definition:** Customers whose most recent subscription record has status `Cancelled`.
- **SQL:** See `sql/03_customer_analysis.sql`, Q3.
- **Business meaning:** Customers who have left the platform; the pool retention efforts aim to shrink.

### New Customers
- **Definition:** Customers whose signup_date falls in the reporting period.
- **SQL:** `GROUP BY strftime('%Y-%m', signup_date)`.
- **Business meaning:** Growth-engine output; tracked alongside churn to gauge net customer growth.

### Churn Rate
- **Definition:** Share of customers (or subscriptions) that have cancelled.
- **Formula:** `Churned Customers / Total Customers`
- **Business meaning:** The single most-watched retention health metric.

### Retention Rate
- **Definition:** The complement of churn rate.
- **Formula:** `1 - Churn Rate`
- **Business meaning:** Positive framing of the same signal; useful for leadership reporting.

### Customer Growth
- **Definition:** Month-over-month percentage change in total customers.
- **Formula:** `(Customers_this_month − Customers_last_month) / Customers_last_month`
- **Business meaning:** Indicates whether acquisition is outpacing churn.

### Average Tenure
- **Definition:** Average number of days between subscription start and
  either cancellation (if churned) or the observation cutoff (if active).
- **Business meaning:** A proxy for product stickiness; longer tenure generally correlates with higher lifetime value.

---

## Revenue KPIs

### Total Revenue
- **Definition:** Sum of successful `Subscription Charge` transaction amounts.
- **SQL:** See `sql/04_revenue_analysis.sql`, Q9.
- **Business meaning:** Realized recurring + one-off revenue collected to date.

### MRR (Monthly Recurring Revenue)
- **Definition:** The normalized monthly value of all currently Active
  subscriptions (annual plans divided by 12).
- **Business meaning:** The standard SaaS metric for predictable recurring revenue run-rate.

### ARPU (Average Revenue Per User)
- **Definition:** Total revenue divided by total customers.
- **SQL:** See `sql/04_revenue_analysis.sql`, Q15.
- **Business meaning:** How much value, on average, each customer relationship generates.

### Revenue Growth %
- **Definition:** Month-over-month percentage change in revenue.
- **SQL:** See `sql/04_revenue_analysis.sql`, Q11 (uses `LAG()`).
- **Business meaning:** Tracks whether the business is scaling revenue, independent of customer count.

### Revenue Lost to Churn
- **Definition:** The annualized recurring value of all cancelled subscriptions
  (monthly price × 12 for monthly plans, monthly_price as-is for annual plans,
  since the stored `monthly_price` on annual subscriptions already reflects
  the discounted annual-equivalent monthly rate).
- **SQL:** See `sql/04_revenue_analysis.sql`, Q16.
- **Business meaning:** The recurring-revenue cost of churn that has already happened.

### Revenue at Risk
- **Definition:** Sum, across Active customers, of `annualized subscription value × predicted churn probability`.
- **Business meaning:** A probability-weighted forecast of revenue likely to be lost if no retention action is taken.

### Customer Lifetime Value (CLV)
- **Definition:** Average historical revenue generated per customer to date (a simple retrospective proxy; not a discounted-future-value model).
- **Business meaning:** A first-order measure of customer value used to prioritize retention spend.

---

## Engagement KPIs

### Average Sessions
- **Definition:** Mean number of product sessions per customer per activity period (~2 weeks).
- **Business meaning:** Core usage-frequency signal.

### Average Session Duration
- **Definition:** Mean session minutes per customer per activity period.
- **Business meaning:** Depth of engagement, complementary to session count.

### Feature Usage
- **Definition:** Mean count of distinct product features used per customer per activity period.
- **Business meaning:** A proxy for how embedded the product is in the customer's workflow.

### Support Tickets
- **Definition:** Count of support tickets filed.
- **Business meaning:** Volume of friction customers are experiencing.

### Average Satisfaction
- **Definition:** Mean post-ticket satisfaction score (1–5 scale).
- **Business meaning:** Quality of the support experience, a known churn driver.

---

## Churn & Risk KPIs (ML-derived)

### Churn Probability
- **Definition:** The predicted probability (0–1) that an Active customer will churn, produced by the project's Random Forest model (`src/churn_model.py`).
- **Business meaning:** Individual-customer risk score used to drive proactive outreach.

### Risk Level
- **Definition:** A categorical bucket derived from Churn Probability using **configurable** thresholds (default: High ≥ 0.70, Medium 0.40–0.69, Low < 0.40 — see `RISK_THRESHOLDS` in `src/churn_model.py`).
- **Business meaning:** A simple triage label for retention teams.

### Retention Priority
- **Definition:** A project-specific business scoring method (not an
  industry-standard formula) that classifies Active customers into 4
  priority tiers by combining churn risk and annualized customer value —
  see Step 19 of `reports/methodology.md`.
- **Business meaning:** Tells a retention team who to call first.
