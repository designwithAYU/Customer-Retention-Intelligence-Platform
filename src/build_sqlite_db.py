"""
build_sqlite_db.py
===================
Loads the cleaned CSVs (data/processed/) into a local SQLite database so the
project's SQL scripts can be executed and validated without requiring a
PostgreSQL/MySQL server to be installed in this environment.

The production schema (sql/01_schema.sql) targets PostgreSQL. This script
creates an equivalent SQLite schema (same tables/columns/constraints, with
PostgreSQL-only syntax such as DISTINCT ON replaced by portable equivalents)
purely for local testing purposes.

Run:
    python src/build_sqlite_db.py
Produces:
    data/processed/novastream.db
"""

import sqlite3
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
DB_PATH = PROCESSED / "novastream.db"

if DB_PATH.exists():
    DB_PATH.unlink()

conn = sqlite3.connect(DB_PATH)

print("Loading processed CSVs into SQLite...")
tables = {
    "customers": ["signup_date"],
    "plans": [],
    "subscriptions": ["start_date", "end_date", "cancellation_date"],
    "transactions": ["transaction_date"],
    "customer_activity": ["activity_date"],
    "support_tickets": ["ticket_date"],
    "marketing_campaigns": ["campaign_date"],
    "customer_campaign_interactions": ["interaction_date"],
}

for table, date_cols in tables.items():
    df = pd.read_csv(PROCESSED / f"{table}.csv", parse_dates=date_cols)
    for c in date_cols:
        df[c] = df[c].dt.strftime("%Y-%m-%d")
    df.to_sql(table, conn, if_exists="replace", index=False)
    print(f"  loaded {table}: {len(df):,} rows")

cur = conn.cursor()

print("Creating indexes...")
index_stmts = [
    "CREATE INDEX idx_subscriptions_customer ON subscriptions(customer_id)",
    "CREATE INDEX idx_subscriptions_plan ON subscriptions(plan_id)",
    "CREATE INDEX idx_subscriptions_status ON subscriptions(subscription_status)",
    "CREATE INDEX idx_transactions_customer ON transactions(customer_id)",
    "CREATE INDEX idx_transactions_subscription ON transactions(subscription_id)",
    "CREATE INDEX idx_activity_customer ON customer_activity(customer_id)",
    "CREATE INDEX idx_tickets_customer ON support_tickets(customer_id)",
    "CREATE INDEX idx_interactions_customer ON customer_campaign_interactions(customer_id)",
]
for stmt in index_stmts:
    cur.execute(stmt)

print("Creating customer_360 view (SQLite-compatible)...")
cur.execute("DROP VIEW IF EXISTS customer_360")
cur.execute("""
CREATE VIEW customer_360 AS
WITH ranked_subs AS (
    SELECT s.*,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY start_date DESC) AS rn
    FROM subscriptions s
),
latest_subscription AS (
    SELECT * FROM ranked_subs WHERE rn = 1
),
revenue AS (
    SELECT customer_id,
           SUM(CASE WHEN transaction_type = 'Subscription Charge' AND payment_status = 'Success' THEN amount ELSE 0 END) AS total_revenue,
           SUM(CASE WHEN transaction_type = 'Subscription Charge' AND payment_status = 'Success' THEN 1 ELSE 0 END) AS total_transactions,
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
    CAST((julianday('2025-09-01') - julianday(c.signup_date)) / 30 AS INTEGER) AS tenure_months
FROM customers c
LEFT JOIN latest_subscription ls ON ls.customer_id = c.customer_id
LEFT JOIN plans p ON p.plan_id = ls.plan_id
LEFT JOIN revenue r ON r.customer_id = c.customer_id
LEFT JOIN engagement e ON e.customer_id = c.customer_id
LEFT JOIN support s ON s.customer_id = c.customer_id
""")

conn.commit()

# quick sanity check
cur.execute("SELECT COUNT(*) FROM customer_360")
print(f"customer_360 view row count: {cur.fetchone()[0]:,}")

conn.close()
print(f"\nSQLite database built at: {DB_PATH}")
