# Data Dictionary

**Project:** Customer Retention Intelligence Platform (NovaStream)

All tables reflect the **cleaned** schema (`data/processed/`). Types shown
are the PostgreSQL types used in `sql/01_schema.sql`.

---

## customers

| Column | Type | Definition | Example | Business meaning |
|---|---|---|---|---|
| customer_id | INTEGER (PK) | Unique customer identifier | 10234 | Natural key for all customer-grain joins |
| signup_date | DATE | Date the customer first signed up | 2024-03-15 | Anchor for tenure and cohort calculations |
| gender | VARCHAR(20) | Self-reported gender | Female | Demographic segmentation |
| age | SMALLINT | Customer age in years (13–100 after cleaning) | 34 | Demographic segmentation |
| country | VARCHAR(60) | Customer's country | Germany | Geographic analysis |
| region | VARCHAR(40) | Aggregated region | Europe | Higher-level geographic rollup |
| acquisition_channel | VARCHAR(40) | How the customer was acquired | Paid Search | Marketing ROI and channel-quality analysis |
| referral_source | VARCHAR(60) | More granular acquisition detail | Friend/Family | Supplementary acquisition context |

## plans

| Column | Type | Definition | Example | Business meaning |
|---|---|---|---|---|
| plan_id | INTEGER (PK) | Unique plan identifier | 3 | Join key to subscriptions |
| plan_name | VARCHAR(30) | Plan display name | Premium | Product tier |
| plan_type | VARCHAR(30) | Individual / Family / Team | Family | Target customer segment |
| monthly_price | NUMERIC(8,2) | List monthly price (USD) | 24.99 | Base pricing |
| max_devices | SMALLINT | Device limit for the plan | 5 | Feature entitlement |
| premium_support | SMALLINT (0/1) | Whether the plan includes premium support | 1 | Feature entitlement |

## subscriptions

| Column | Type | Definition | Example | Business meaning |
|---|---|---|---|---|
| subscription_id | INTEGER (PK) | Unique subscription record | 44210 | A customer may have >1 (reactivations) |
| customer_id | INTEGER (FK) | Owning customer | 10234 | Join to customers |
| plan_id | INTEGER (FK) | Plan on this subscription | 3 | Join to plans |
| start_date | DATE | Subscription start date | 2024-03-15 | Tenure anchor |
| end_date | DATE (nullable) | Subscription end date (NULL if still active) | 2024-11-02 | Churn timing |
| billing_cycle | VARCHAR(10) | Monthly / Annual | Monthly | Key churn driver |
| monthly_price | NUMERIC(8,2) | Actual price paid per month (after discount) | 19.99 | Realized pricing |
| discount_percentage | SMALLINT | Discount applied (0–100) | 20 | Promotional impact analysis |
| subscription_status | VARCHAR(15) | Active / Cancelled | Cancelled | Primary churn label |
| cancellation_date | DATE (nullable) | Date of cancellation | 2024-11-02 | Churn timing, cohort analysis |
| cancellation_reason | VARCHAR(60) (nullable) | Stated reason for cancellation | "Too expensive" | Root-cause analysis |

## transactions

| Column | Type | Definition | Example | Business meaning |
|---|---|---|---|---|
| transaction_id | INTEGER (PK) | Unique transaction | 881023 | Billing event identifier |
| customer_id | INTEGER (FK) | Customer billed | 10234 | Join to customers |
| subscription_id | INTEGER (FK) | Subscription billed | 44210 | Join to subscriptions |
| transaction_date | DATE | Date of the transaction | 2024-04-15 | Revenue timing |
| transaction_type | VARCHAR(30) | Subscription Charge / Add-on Purchase | Subscription Charge | Revenue categorization |
| amount | NUMERIC(10,2) | Transaction amount (USD) | 19.99 | Revenue value |
| discount_amount | NUMERIC(10,2) | Dollar value of discount applied | 4.00 | Promotional cost tracking |
| payment_status | VARCHAR(15) | Success / Failed / Refunded / Unknown | Success | Revenue recognition filter |

## customer_activity

| Column | Type | Definition | Example | Business meaning |
|---|---|---|---|---|
| activity_id | INTEGER (PK) | Unique activity snapshot | 512004 | Engagement record identifier |
| customer_id | INTEGER (FK) | Customer | 10234 | Join to customers |
| activity_date | DATE | Start of the ~2-week snapshot period | 2024-04-01 | Engagement timing |
| sessions | INTEGER | Number of product sessions in the period | 9 | Usage frequency |
| session_minutes | INTEGER | Total minutes across sessions | 142 | Usage depth |
| content_consumed | INTEGER | Units of content consumed | 7 | Product-specific engagement |
| feature_usage_count | INTEGER | Distinct feature-use events | 5 | Feature adoption |

## support_tickets

| Column | Type | Definition | Example | Business meaning |
|---|---|---|---|---|
| ticket_id | INTEGER (PK) | Unique ticket | 33021 | Support event identifier |
| customer_id | INTEGER (FK) | Customer | 10234 | Join to customers |
| ticket_date | DATE | Date filed | 2024-06-02 | Support-load timing |
| issue_type | VARCHAR(40) | Category of issue | Billing | Root-cause categorization |
| resolution_time_hours | NUMERIC(6,1) | Hours to resolve | 14.5 | Support quality/SLA tracking |
| satisfaction_score | SMALLINT (1–5) | Post-ticket CSAT | 3 | Support quality, churn driver |
| ticket_status | VARCHAR(25) | Resolved / Escalated / Closed - Unresolved | Resolved | Outcome tracking |

## marketing_campaigns

| Column | Type | Definition | Example | Business meaning |
|---|---|---|---|---|
| campaign_id | INTEGER (PK) | Unique campaign | 42 | Campaign identifier |
| campaign_date | DATE | Campaign launch date | 2024-02-10 | Timing |
| channel | VARCHAR(40) | Channel used | Social Media | Channel-level ROI |
| campaign_type | VARCHAR(30) | Awareness / Promotion / Retargeting / Retention / Referral Bonus | Retention | Campaign intent |
| spend | NUMERIC(10,2) | Campaign spend (USD) | 2450.00 | Marketing cost |

## customer_campaign_interactions

| Column | Type | Definition | Example | Business meaning |
|---|---|---|---|---|
| interaction_id | INTEGER (PK) | Unique interaction | 990211 | Interaction identifier |
| customer_id | INTEGER (FK) | Customer | 10234 | Join to customers |
| campaign_id | INTEGER (FK) | Campaign | 42 | Join to marketing_campaigns |
| interaction_type | VARCHAR(20) | Email Open / Click / Ad View / Conversion / Unsubscribe | Click | Funnel stage |
| interaction_date | DATE | Date of interaction | 2024-02-12 | Timing |

---

## Derived / output tables

| Table | Location | Grain | Notes |
|---|---|---|---|
| customer_360 | SQL view (`sql/01_schema.sql`) | 1 row per customer | Combines demographics, latest subscription, revenue, engagement, support, churn flag |
| feature_table.csv | `data/processed/` | 1 row per customer | Leakage-safe ML feature table (see `src/feature_engineering.py`) |
| customer_segments.csv | `outputs/tables/` | 1 row per customer | RFM scores + segment label |
| customer_churn_risk.csv | `outputs/model_results/` | 1 row per customer | churn_probability + risk_level |
| retention_priority.csv | `outputs/tables/` | 1 row per Active customer | Business-defined retention priority tier |
| cohort_retention.csv | `outputs/tables/` | 1 row per signup-month cohort | Retention % at M0/M1/M2/M3/M6/M12 |
