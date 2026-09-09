# Methodology

**Project:** Customer Retention Intelligence Platform (NovaStream)

This document explains the end-to-end approach taken in this project, step
by step, and the reasoning behind key decisions.

## 1. Business Problem

NovaStream (a fictional subscription/SaaS company) has rising churn and no
systematic way to answer: **who is churning, why, how much revenue is at
risk, and who should be prioritized for retention?** This project builds an
end-to-end analytics solution — SQL, Python, statistics, ML, and a Power BI
specification — to answer those questions using data an analyst would
plausibly have access to (subscriptions, billing, product usage, support,
and marketing interaction logs).

## 2. Data Generation

No suitable public dataset combines subscription billing, product
engagement, support tickets, and marketing interactions at this scale, so a
synthetic dataset was generated (`src/generate_data.py`). Rather than
hand-coding fixed churn rates per segment, churn is driven by a **latent
risk score** per customer, built from acquisition channel, plan, billing
cycle, age, discount, and a random per-customer "frailty" term (unobserved
heterogeneity), converted to a monthly hazard via a logistic function and
simulated month-by-month (a discrete-time survival model). Engagement,
satisfaction, and support-ticket behavior are generated as correlated (not
identical) functions of that same latent risk plus independent noise, so
that patterns discovered later in EDA and modeling are *emergent* from the
simulation rather than manually scripted. See the module docstring in
`src/generate_data.py` for full detail.

## 3. Data Quality

Realistic data-quality problems (missing values ~1-4% per field, duplicate
customers/transactions, inconsistent capitalization, impossible ages,
orphaned foreign keys, cancelled subscriptions missing a cancellation date,
invalid negative charges) were injected on top of the "clean" simulation
output, so the cleaning stage has genuine problems to discover — see
`reports/data_quality_report.md`.

## 4. Cleaning

`src/clean_data.py` loads each raw table, profiles it, and applies
documented treatments (deduplication, standardization, imputation,
exclusion of unrecoverable orphan records). Every treatment is logged with
the number/percentage of records affected and the reasoning, and written to
`reports/data_quality_report.md`.

## 5. SQL

`sql/01_schema.sql` defines a normalized PostgreSQL schema plus a
`customer_360` analytical view. `sql/02_data_quality.sql` re-validates the
cleaned data. `sql/03`–`07` contain 47 numbered business questions across
Customer Analysis, Revenue Analysis, Churn Analysis, Customer Behavior,
Retention, and Advanced Analysis, using CTEs, window functions, and
aggregate logic. All queries were executed and validated against a SQLite
build of the same schema (`src/build_sqlite_db.py`, `src/test_sql.py`)
since a PostgreSQL/MySQL server is not available in this development
environment — see the note in `README.md` → *How to Run*.

## 6. EDA

`src/eda.py` produces 17 core business-question-driven charts (age
distribution, growth, revenue trend, plan mix, channel mix, churn cuts by
plan/billing/support/satisfaction/age, engagement comparisons, tenure at
churn, revenue by region, discount effect), each framed explicitly as the
business question it answers.

## 7. RFM Segmentation

`src/segmentation.py` computes Recency (days since last successful
transaction), Frequency (transaction count), and Monetary (total revenue)
per customer, scores each 1–5 by quintile, and assigns one of 7 business
segments (VIP, Loyal, Potential Loyal, New, At Risk, Dormant, Lost) using a
transparent rule set (documented in the module). Segment size, revenue
share, and churn rate are computed and exported to
`outputs/tables/customer_segments.csv`.

## 8. Cohort Analysis

`src/cohort_analysis.py` groups customers by signup month and computes
retention at M0/M1/M2/M3/M6/M12, producing both a retention matrix
(`outputs/tables/cohort_retention.csv`) and a heatmap. A simple early-vs-late
cohort comparison checks whether retention is trending up or down over time.

## 9. Statistical Analysis

`src/statistical_analysis.py` runs independent t-tests (continuous
variables: tenure, price, engagement, ticket count, satisfaction) and
chi-square tests of independence (categorical variables: billing cycle,
plan, acquisition channel) between churned and retained customers, plus a
point-biserial correlation between engagement and churn. **Every result is
reported as an association, with an explicit note that association does not
imply causation** — see `outputs/tables/statistical_tests.csv` and the
caveat printed by the script.

## 10. Churn Modeling

`src/feature_engineering.py` builds a leakage-safe, customer-level feature
table. Critically, all time-varying features (engagement, support, revenue)
are computed **only using records dated on or before each customer's own
observation cutoff** — their cancellation date if churned, or the global
data cutoff if still active — mirroring how a model would be scored in
production. `cancellation_date` and `cancellation_reason` are excluded from
features entirely.

`src/churn_model.py` trains Logistic Regression and Random Forest
(scikit-learn), using `class_weight="balanced"` to handle the moderate
(~20%) class imbalance rather than synthetic oversampling (SMOTE was
considered but judged unnecessary for this imbalance ratio, and avoided to
keep the training data auditable/traceable to real observations). Both
models are evaluated on a held-out 25% test split with Accuracy, Precision,
Recall, F1, ROC-AUC, and a confusion matrix; **Random Forest was selected**
for its materially higher ROC-AUC (see `reports/business_insights.md` for
the actual scores). Because a missed churner is more costly than a false
alarm for a retention team, **recall** is discussed as the more
business-relevant metric alongside AUC.

## 11. Revenue-at-Risk

Revenue at Risk = `annualized subscription value × churn probability`,
summed across Active customers. This is a standard expected-value framing:
it does not assume every high-probability customer will definitely churn,
but weights each customer's potential revenue loss by how likely that loss
is.

## 12. Power BI

`powerbi/dashboard_specification.md`, `dax_measures.md`, and
`data_model.md` provide a complete 5-page dashboard spec (Executive
Overview, Customer Segmentation, Churn & Retention, Revenue Intelligence,
Retention Action Center), star-schema relationships, and DAX measure
definitions, so the report can be built or imported directly against
`data/processed/` and `outputs/`.

## 13. Recommendations

`reports/business_insights.md` and `reports/executive_summary.md` translate
findings into specific, evidence-linked recommendations (see those
documents). No recommendation claims a specific improvement percentage
unless it was actually measured in this project.

## 14. Limitations

- **Synthetic data:** while designed to be statistically realistic and
  noisy (not hand-tuned to produce "clean" results), it is not real
  NovaStream data, and absolute figures should not be treated as real
  business benchmarks.
- **CLV proxy:** Customer Lifetime Value here is a *retrospective* average
  of realized revenue, not a discounted-future-value or cohort-based
  forward LTV model.
- **Revenue-at-Risk is a point estimate:** it does not model retention
  campaign uptake, cost, or ROI (see the A/B test proposal in
  `reports/business_insights.md` for how a real experiment would validate
  interventions before broad rollout).
- **No real PostgreSQL/MySQL server was available in the development
  environment** used to build this project. All SQL was written for
  PostgreSQL syntax and additionally validated end-to-end against an
  equivalent SQLite build (`src/build_sqlite_db.py`) to guarantee every
  query actually executes correctly.
- **Model recall/precision trade-off** was tuned for the default 0.5
  classification threshold; a production deployment would likely tune the
  threshold (or use the configurable risk tiers) against actual retention
  team capacity.
