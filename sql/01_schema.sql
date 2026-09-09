-- ===========================================================================
-- 01_schema.sql
-- NovaStream Customer Retention Intelligence Platform
-- Target engine: PostgreSQL 14+
-- (A SQLite-compatible copy of this schema is produced automatically by
--  src/build_sqlite_db.py for local testing where PostgreSQL is unavailable.)
-- ===========================================================================

DROP TABLE IF EXISTS customer_campaign_interactions CASCADE;
DROP TABLE IF EXISTS marketing_campaigns CASCADE;
DROP TABLE IF EXISTS support_tickets CASCADE;
DROP TABLE IF EXISTS customer_activity CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS subscriptions CASCADE;
DROP TABLE IF EXISTS plans CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

-- ---------------------------------------------------------------------------
-- customers
-- ---------------------------------------------------------------------------
CREATE TABLE customers (
    customer_id           INTEGER PRIMARY KEY,
    signup_date           DATE NOT NULL,
    gender                VARCHAR(20),
    age                   SMALLINT CHECK (age BETWEEN 13 AND 100),
    country               VARCHAR(60),
    region                VARCHAR(40),
    acquisition_channel   VARCHAR(40),
    referral_source       VARCHAR(60)
);

-- ---------------------------------------------------------------------------
-- plans
-- ---------------------------------------------------------------------------
CREATE TABLE plans (
    plan_id         INTEGER PRIMARY KEY,
    plan_name       VARCHAR(30) NOT NULL,
    plan_type       VARCHAR(30),
    monthly_price   NUMERIC(8,2) NOT NULL CHECK (monthly_price >= 0),
    max_devices     SMALLINT,
    premium_support SMALLINT CHECK (premium_support IN (0,1))
);

-- ---------------------------------------------------------------------------
-- subscriptions
-- ---------------------------------------------------------------------------
CREATE TABLE subscriptions (
    subscription_id       INTEGER PRIMARY KEY,
    customer_id           INTEGER NOT NULL REFERENCES customers(customer_id),
    plan_id               INTEGER NOT NULL REFERENCES plans(plan_id),
    start_date            DATE NOT NULL,
    end_date              DATE,
    billing_cycle         VARCHAR(10) CHECK (billing_cycle IN ('Monthly','Annual')),
    monthly_price         NUMERIC(8,2) NOT NULL CHECK (monthly_price >= 0),
    discount_percentage   SMALLINT DEFAULT 0 CHECK (discount_percentage BETWEEN 0 AND 100),
    subscription_status   VARCHAR(15) CHECK (subscription_status IN ('Active','Cancelled')),
    cancellation_date     DATE,
    cancellation_reason   VARCHAR(60),
    CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE INDEX idx_subscriptions_customer ON subscriptions(customer_id);
CREATE INDEX idx_subscriptions_plan ON subscriptions(plan_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(subscription_status);
CREATE INDEX idx_subscriptions_start ON subscriptions(start_date);

-- ---------------------------------------------------------------------------
-- transactions
-- ---------------------------------------------------------------------------
CREATE TABLE transactions (
    transaction_id     INTEGER PRIMARY KEY,
    customer_id        INTEGER NOT NULL REFERENCES customers(customer_id),
    subscription_id    INTEGER NOT NULL REFERENCES subscriptions(subscription_id),
    transaction_date   DATE NOT NULL,
    transaction_type   VARCHAR(30),
    amount             NUMERIC(10,2) NOT NULL,
    discount_amount    NUMERIC(10,2) DEFAULT 0,
    payment_status     VARCHAR(15)
);

CREATE INDEX idx_transactions_customer ON transactions(customer_id);
CREATE INDEX idx_transactions_subscription ON transactions(subscription_id);
CREATE INDEX idx_transactions_date ON transactions(transaction_date);

-- ---------------------------------------------------------------------------
-- customer_activity
-- ---------------------------------------------------------------------------
CREATE TABLE customer_activity (
    activity_id            INTEGER PRIMARY KEY,
    customer_id            INTEGER NOT NULL REFERENCES customers(customer_id),
    activity_date          DATE NOT NULL,
    sessions               INTEGER DEFAULT 0,
    session_minutes        INTEGER DEFAULT 0,
    content_consumed       INTEGER DEFAULT 0,
    feature_usage_count    INTEGER DEFAULT 0
);

CREATE INDEX idx_activity_customer ON customer_activity(customer_id);
CREATE INDEX idx_activity_date ON customer_activity(activity_date);

-- ---------------------------------------------------------------------------
-- support_tickets
-- ---------------------------------------------------------------------------
CREATE TABLE support_tickets (
    ticket_id               INTEGER PRIMARY KEY,
    customer_id             INTEGER NOT NULL REFERENCES customers(customer_id),
    ticket_date             DATE NOT NULL,
    issue_type              VARCHAR(40),
    resolution_time_hours   NUMERIC(6,1),
    satisfaction_score      SMALLINT CHECK (satisfaction_score BETWEEN 1 AND 5),
    ticket_status           VARCHAR(25)
);

CREATE INDEX idx_tickets_customer ON support_tickets(customer_id);

-- ---------------------------------------------------------------------------
-- marketing_campaigns
-- ---------------------------------------------------------------------------
CREATE TABLE marketing_campaigns (
    campaign_id     INTEGER PRIMARY KEY,
    campaign_date   DATE NOT NULL,
    channel         VARCHAR(40),
    campaign_type   VARCHAR(30),
    spend           NUMERIC(10,2)
);

-- ---------------------------------------------------------------------------
-- customer_campaign_interactions
-- ---------------------------------------------------------------------------
CREATE TABLE customer_campaign_interactions (
    interaction_id     INTEGER PRIMARY KEY,
    customer_id        INTEGER NOT NULL REFERENCES customers(customer_id),
    campaign_id        INTEGER NOT NULL REFERENCES marketing_campaigns(campaign_id),
    interaction_type   VARCHAR(20),
    interaction_date   DATE NOT NULL
);

CREATE INDEX idx_interactions_customer ON customer_campaign_interactions(customer_id);
CREATE INDEX idx_interactions_campaign ON customer_campaign_interactions(campaign_id);

-- ===========================================================================
-- customer_360 : the core analytical view
-- Combines demographics, subscription, revenue, engagement, support and
-- RFM/churn signals into a single customer-grain view for BI and analysis.
-- ===========================================================================
CREATE OR REPLACE VIEW customer_360 AS
WITH latest_subscription AS (
    SELECT DISTINCT ON (customer_id) *
    FROM subscriptions
    ORDER BY customer_id, start_date DESC
),
revenue AS (
    SELECT customer_id,
           SUM(amount) FILTER (WHERE transaction_type = 'Subscription Charge' AND payment_status = 'Success') AS total_revenue,
           COUNT(*) FILTER (WHERE transaction_type = 'Subscription Charge' AND payment_status = 'Success') AS total_transactions,
           MAX(transaction_date) AS last_transaction_date
    FROM transactions
    GROUP BY customer_id
),
engagement AS (
    SELECT customer_id,
           AVG(sessions) AS avg_sessions,
           AVG(session_minutes) AS avg_session_minutes,
           AVG(feature_usage_count) AS avg_feature_usage,
           MAX(activity_date) AS last_activity_date
    FROM customer_activity
    GROUP BY customer_id
),
support AS (
    SELECT customer_id,
           COUNT(*) AS total_tickets,
           AVG(satisfaction_score) AS avg_satisfaction,
           SUM(CASE WHEN ticket_status = 'Closed - Unresolved' THEN 1 ELSE 0 END) AS unresolved_tickets
    FROM support_tickets
    GROUP BY customer_id
)
SELECT
    c.customer_id,
    c.signup_date,
    c.age,
    c.gender,
    c.country,
    c.region,
    c.acquisition_channel,
    ls.plan_id,
    p.plan_name,
    ls.billing_cycle,
    ls.monthly_price,
    ls.discount_percentage,
    ls.subscription_status,
    ls.cancellation_date,
    ls.cancellation_reason,
    COALESCE(r.total_revenue, 0) AS total_revenue,
    COALESCE(r.total_transactions, 0) AS total_transactions,
    r.last_transaction_date,
    COALESCE(e.avg_sessions, 0) AS avg_sessions,
    COALESCE(e.avg_session_minutes, 0) AS avg_session_minutes,
    COALESCE(e.avg_feature_usage, 0) AS avg_feature_usage,
    e.last_activity_date,
    COALESCE(s.total_tickets, 0) AS total_tickets,
    s.avg_satisfaction,
    COALESCE(s.unresolved_tickets, 0) AS unresolved_tickets,
    CASE WHEN ls.subscription_status = 'Cancelled' THEN 1 ELSE 0 END AS is_churned,
    (CURRENT_DATE - c.signup_date) / 30 AS tenure_months
FROM customers c
LEFT JOIN latest_subscription ls ON ls.customer_id = c.customer_id
LEFT JOIN plans p ON p.plan_id = ls.plan_id
LEFT JOIN revenue r ON r.customer_id = c.customer_id
LEFT JOIN engagement e ON e.customer_id = c.customer_id
LEFT JOIN support s ON s.customer_id = c.customer_id;

-- Note: DISTINCT ON is PostgreSQL-specific. The SQLite-compatible build
-- (src/build_sqlite_db.py) creates an equivalent view using a window-function
-- ROW_NUMBER() pattern, since SQLite does not support DISTINCT ON.
