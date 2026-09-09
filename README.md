# Customer Retention Intelligence Platform

**An end-to-end SQL + Python + Power BI analytics project for a fictional subscription/SaaS company, NovaStream.**

![Python](https://img.shields.io/badge/Python-3.12-blue)
![SQL](https://img.shields.io/badge/SQL-PostgreSQL-336791)
![Power BI](https://img.shields.io/badge/BI-Power%20BI-F2C811)
![scikit--learn](https://img.shields.io/badge/ML-scikit--learn-orange)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Overview

NovaStream is a fictional subscription/SaaS company facing rising customer
churn with no systematic way to understand it. This project builds a
complete analytics solution — from raw, messy data through cleaning, SQL
analysis, exploratory data analysis, RFM segmentation, cohort analysis,
statistical testing, and machine-learning churn prediction — to a
Power BI-ready dashboard specification, answering one question:

> **Who is churning, why, how much revenue is at risk, and who should the business prioritize to retain?**

This is a **Data Analyst portfolio project**. SQL, Python/pandas, EDA,
business analytics, Power BI/DAX, statistics, and customer segmentation are
the primary focus; machine learning is a secondary, supporting component.

---

## Business Problem

Management has noticed churn increasing but lacks visibility into:
- Why customers churn
- Which customers are likely to churn next
- Which plans/channels/segments drive the most churn and the most value
- How much revenue is at risk
- Who to prioritize for retention outreach

---

## Objectives

1. Generate a realistic, appropriately messy dataset (no public dataset
   combines billing + engagement + support + marketing at this grain).
2. Clean it and document every data-quality issue found.
3. Answer 47 real business questions in SQL.
4. Explore the data visually (17+ charts, each tied to a business question).
5. Segment customers with RFM.
6. Run cohort retention analysis.
7. Test statistical associations between churn and key drivers.
8. Predict churn with Logistic Regression and Random Forest (leakage-safe).
9. Quantify revenue at risk and build a retention-priority worklist.
10. Specify a 5-page Power BI dashboard with DAX measures.
11. Translate all of the above into business insights and recommendations.

---

## Dataset

Synthetic, generated in `src/generate_data.py`, sized well above the
project's original targets:

| Table | Rows |
|---|---:|
| customers | 52,000 |
| subscriptions | 52,563 |
| transactions | 393,498 |
| customer_activity | 976,631 |
| support_tickets | 78,233 |
| marketing_campaigns | 180 |
| customer_campaign_interactions | 103,769 |

**Design philosophy:** churn is driven by a *latent risk score* per
customer (acquisition channel + plan + billing cycle + age + discount +
random per-customer noise), converted into a monthly hazard and simulated
month-by-month — not a hardcoded "Plan A = 50% churn" lookup table.
Engagement, satisfaction, and support behavior are correlated with that same
latent risk plus independent noise, so relationships discovered later in
EDA/modeling are *emergent*, not manufactured. See the docstring in
`src/generate_data.py` for full detail. Realistic data-quality problems
(missing values, duplicates, bad labels, orphan foreign keys, impossible
ages) are then injected on top.

---

## Data Architecture

8 normalized tables (`customers`, `plans`, `subscriptions`, `transactions`,
`customer_activity`, `support_tickets`, `marketing_campaigns`,
`customer_campaign_interactions`) plus a `customer_360` analytical view that
joins demographics, subscription, revenue, engagement, support, and churn
status into one customer-grain view. Full schema: `sql/01_schema.sql`.
Column-level definitions: `reports/data_dictionary.md`.

---

## Data Cleaning

`src/clean_data.py` finds and fixes duplicate customers, inconsistent
capitalization, impossible ages, cancelled subscriptions missing a
cancellation date, invalid negative charges, orphaned foreign keys, and
more — every issue logged with records affected and treatment applied in
**`reports/data_quality_report.md`**.

---

## SQL Analysis

47 numbered business queries across 5 files (`sql/03`–`07`), covering
Customer Analysis, Revenue Analysis, Churn Analysis, Customer Behavior,
Retention/Cohort Analysis, and Advanced Analysis, using CTEs, window
functions (`ROW_NUMBER`, `NTILE`, `LAG`), `CASE`, joins, and aggregates.
`sql/02_data_quality.sql` re-validates the cleaned data. All queries were
executed and validated end-to-end (`src/test_sql.py`, 59/59 statements
pass) — see *How to Run* below for the PostgreSQL/SQLite note.

---

## KPI Framework

A full KPI dictionary (definition, formula, SQL, business meaning) for
Customer, Revenue, and Engagement KPIs lives in `reports/kpi_dictionary.md`.

---

## Exploratory Data Analysis

`src/eda.py` generates 17 charts (age distribution, customer growth,
revenue trend, plan/channel mix, churn cuts by plan/billing/support/
satisfaction/age/discount, engagement comparisons, tenure-at-churn), plus a
cohort retention heatmap (`src/cohort_analysis.py`) — **18 figures total**
in `outputs/figures/`. Notebook: `notebooks/03_exploratory_analysis.ipynb`.

---

## Customer Segmentation

RFM (Recency/Frequency/Monetary) scoring assigns every customer to one of 7
segments: VIP, Loyal, Potential Loyal, New, At Risk, Dormant, Lost
(`src/segmentation.py`). VIP + Dormant customers together hold **51.9%** of
all revenue. Full segment table: `outputs/tables/customer_segments.csv`.

---

## Cohort Analysis

Monthly signup cohorts, retention tracked at M0/M1/M2/M3/M6/M12
(`src/cohort_analysis.py`). Early vs. late cohort M3 retention is
essentially flat (90.9% vs. 91.0%) — churn is better explained by
plan/billing/engagement drivers than a worsening cohort trend. See
`outputs/tables/cohort_retention.csv` and
`outputs/figures/18_cohort_retention_heatmap.png`.

---

## Churn Prediction

`src/feature_engineering.py` builds a **leakage-safe** feature table:
`cancellation_date`/`cancellation_reason` are excluded, and every
time-varying feature is computed only from records dated on or before each
customer's own observation cutoff (mirroring real-time scoring).

`src/churn_model.py` trains and evaluates Logistic Regression and Random
Forest (`class_weight="balanced"` for the ~20% churn class imbalance,
chosen over SMOTE for simplicity/auditability):

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---:|---:|---:|---:|---:|
| Logistic Regression | 65.01% | 33.77% | 72.34% | 46.04% | 0.7407 |
| **Random Forest (selected)** | **89.42%** | **70.95%** | **82.48%** | **76.28%** | **0.9447** |

Top predictors: `recency_days`, `tenure_days`, `total_transactions`,
`total_revenue`, `engagement_trend_ratio`. Recall is highlighted as the
business-critical metric: missing an at-risk customer is costlier than a
false alarm for a retention team.

Configurable risk tiers (`src/churn_model.py`, `RISK_THRESHOLDS`): High ≥
0.70, Medium 0.40–0.69, Low < 0.40. Every customer's score:
`outputs/model_results/customer_churn_risk.csv`.

---

## Model Performance

See table above. Full comparison: `outputs/model_results/model_comparison.csv`.
ROC curve, confusion matrices, and feature importance charts:
`outputs/figures/roc_curve.png`, `confusion_matrices.png`, `feature_importance.png`.

---

## Revenue at Risk

`Revenue at Risk = annualized subscription value × churn probability`,
summed across Active customers = **$1,255,230.23**. A 4-tier Retention
Priority score (`Priority 1`: High Risk/High Value → `Priority 4`: Low Risk)
ranks every Active customer for outreach: `outputs/tables/retention_priority.csv`.

---

## Power BI Dashboard

A complete 5-page dashboard specification — **Executive Overview**,
**Customer Segmentation**, **Churn & Retention**, **Revenue Intelligence**,
**Retention Action Center** — with a star-schema data model and full DAX
measure library:
- `powerbi/dashboard_specification.md`
- `powerbi/data_model.md`
- `powerbi/dax_measures.md`

---

## Key Insights

10 evidence-linked findings in `reports/business_insights.md`. Highlights:
- Monthly-billing churn (23.5%) is ~9 points higher than annual (14.6%).
- Basic-plan churn (24.3%) is ~1.6x Enterprise churn (14.8%).
- The top revenue decile (10% of customers) drives **33%** of all revenue.
- 5,407 high-value Active customers currently show low satisfaction or an
  unresolved ticket — **$2.38M** in revenue exposure.

## Business Recommendations

See `reports/business_insights.md` (full list) and
`reports/executive_summary.md` (leadership-level summary): onboarding
investment in the first 90 days, annual-plan incentives, automated
engagement/support alerts, a VIP retention track, and a proposed A/B test to
validate any intervention before broad rollout.

---

## Technology Stack

- **Python:** pandas, NumPy, scikit-learn, SciPy, matplotlib, seaborn
- **Database:** PostgreSQL (schema target) — validated locally via SQLite
- **BI:** Power BI-ready datasets + DAX measure documentation
- **ML:** Logistic Regression, Random Forest (scikit-learn)
- **Dev:** Git, VS Code-compatible, Jupyter notebooks

---

## Project Structure

```
customer-retention-intelligence/
├── data/
│   ├── raw/                 # generated raw CSVs (messy, pre-cleaning)
│   └── processed/           # cleaned CSVs + novastream.db (SQLite test DB)
├── sql/                      # 01_schema .. 07_advanced_analysis (47 queries)
├── notebooks/                 # 5 real, executed Jupyter notebooks
├── src/                       # all pipeline & analysis code
├── outputs/
│   ├── figures/               # 21 PNG charts
│   ├── tables/                # segments, cohort table, retention priority, stats
│   └── model_results/         # model comparison, feature importance, risk scores
├── powerbi/                    # dashboard spec, DAX measures, data model
├── reports/                    # data quality, KPI dict, data dict, methodology,
│                                # business insights, executive summary
├── screenshots/
├── requirements.txt
├── README.md
├── .gitignore
└── LICENSE
```

---

## How to Run

```bash
# 1. Set up environment
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Generate the raw synthetic dataset
python src/generate_data.py

# 3. Clean it (writes data/processed/ + reports/data_quality_report.md)
python src/clean_data.py

# 4. Build a local SQLite database for SQL validation
#    (this project targets PostgreSQL — sql/01_schema.sql — but no DB
#    server is assumed to be installed locally; this step builds an
#    equivalent SQLite DB so every query can be run and checked end-to-end)
python src/build_sqlite_db.py
python src/test_sql.py           # runs & validates all 47+ business queries

# 5. Run the analysis pipeline
python src/eda.py                       # 17 EDA charts
python src/cohort_analysis.py           # cohort table + heatmap
python src/segmentation.py              # RFM segments
python src/statistical_analysis.py      # t-tests / chi-square
python src/feature_engineering.py       # leakage-safe ML feature table
python src/churn_model.py               # train, evaluate, score, prioritize

# 6. (Optional) rebuild the Jupyter notebooks with fresh outputs
python src/build_notebooks.py

# 7. Open the Power BI docs (powerbi/) in Power BI Desktop, or explore the
#    notebooks in notebooks/ with Jupyter/VS Code.
```

**Running against real PostgreSQL instead of SQLite:** create a database,
then `psql -d novastream -f sql/01_schema.sql`, then load
`data/processed/*.csv` with `\copy` or your preferred ETL tool, then run
`sql/02` through `sql/07` directly — no changes needed, since
`sql/01_schema.sql` is written in standard PostgreSQL syntax.

---

## Limitations

- Synthetic (not real production) data — absolute dollar figures illustrate
  the *method*, not real NovaStream financials.
- CLV is a retrospective average, not a discounted forward-looking model.
- No PostgreSQL/MySQL server was available in the build environment; all
  SQL is PostgreSQL-targeted and additionally validated via an equivalent
  SQLite build.
- Statistical findings are associations in observational data, not proven
  causal effects.

## Future Improvements

- Real-time model re-scoring pipeline (e.g. daily batch job).
- Survival-analysis (Cox proportional hazards) model for time-to-churn.
- True forward-looking CLV model incorporating retention probability.
- Actual A/B test execution of the proposed retention intervention.
- Power BI `.pbix` file built directly, once a licensed Power BI Desktop
  environment is available (this repo currently ships a complete,
  ready-to-build specification instead).

---

## Resume Bullets

- Built an end-to-end customer retention analytics platform using SQL,
  Python, and Power BI, analyzing **52,000 customers** and **393,498
  transactions** to quantify churn drivers across plans, billing cycles,
  cohorts, and acquisition channels.
- Developed RFM segmentation, cohort retention analysis, and a leakage-safe
  Random Forest churn model achieving **0.94 ROC-AUC / 82.5% recall**,
  identifying **$1.26M** in probability-weighted revenue at risk.
- Designed a 5-page Power BI dashboard specification with **20+ DAX
  measures** tracking churn, retention, MRR, CLV, and revenue at risk,
  enabling a data-driven, priority-ranked customer retention worklist.
