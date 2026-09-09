"""
build_notebooks.py
==================

Constructs the 5 project notebooks by ACTUALLY EXECUTING the analysis code
via nb_utils.NotebookBuilder and embedding genuine text/figure outputs.

Run:
    python src/build_notebooks.py
"""

from pathlib import Path
import sys
import subprocess

from nb_utils import NotebookBuilder


# ===========================================================================
# PROJECT PATHS
# ===========================================================================

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
NB_DIR = ROOT / "notebooks"

NB_DIR.mkdir(parents=True, exist_ok=True)

# Make sure Python can find project modules.
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC_DIR))


# ===========================================================================
# Helper function
# ===========================================================================

def run_script(script_name):
    """
    Run a Python script from the src directory.
    """

    result = subprocess.run(
        [sys.executable, str(SRC_DIR / script_name)],
        cwd=str(ROOT),
        capture_output=True,
        text=True
    )

    print(result.stdout)

    if result.stderr:
        print("STDERR:")
        print(result.stderr)

    return result


# ===========================================================================
# 01_data_generation.ipynb
# ===========================================================================
nb = NotebookBuilder()
nb.namespace["ROOT"] = ROOT
nb.namespace["run_script"] = run_script

nb.markdown(
"""# 01 — Data Generation

**NovaStream Customer Retention Intelligence Platform**

This notebook documents how the synthetic NovaStream dataset was generated.

The full generation logic lives in `src/generate_data.py`.

Design principles used in generation:

- Churn is driven by a latent risk score built from acquisition channel,
  plan, billing cycle, age, discount, and customer-level random variation.
- Engagement, satisfaction, and support-ticket behavior are correlated with
  the same underlying risk plus independent noise.
- Realistic data-quality problems such as missing values, duplicates,
  inconsistent labels, and orphan foreign keys are injected into the raw data.
"""
)

nb.code(
"""
result = run_script("generate_data.py")

if result.returncode != 0:
    print("Data generation failed.")
"""
)


nb.markdown("## Inspect the generated raw tables")

nb.code(
"""
import pandas as pd

RAW = ROOT / "data" / "raw"

tables = {}

for name in [
    "customers",
    "plans",
    "subscriptions",
    "transactions",
    "customer_activity",
    "support_tickets",
    "marketing_campaigns",
    "customer_campaign_interactions"
]:
    tables[name] = pd.read_csv(RAW / f"{name}.csv")
    print(f"{name:35s} shape={tables[name].shape}")
"""
)

nb.code(
"""
tables["customers"].head()
"""
)

nb.code(
"""
print("customers.csv head:")
print(tables["customers"].head().to_string())
"""
)

nb.code(
"""
print("Sample of injected data-quality problems:")

print(
    "- Duplicate customer_id count:",
    tables["customers"]["customer_id"].duplicated().sum()
)

print(
    "- Missing ages:",
    tables["customers"]["age"].isna().sum()
)

print(
    "- Ages out of plausible range:",
    (
        (tables["customers"]["age"] < 0)
        |
        (tables["customers"]["age"] > 100)
    ).sum()
)

print(
    "- Upper-case country values:",
    tables["customers"]["country"]
    .dropna()
    .apply(lambda x: isinstance(x, str) and x.isupper())
    .sum()
)
"""
)

nb.code(
"""
subs = tables["subscriptions"]

churn_rate = (
    subs["subscription_status"]
    .str.lower()
    .eq("cancelled")
    .mean()
)

print(f"Raw subscription-level churn rate: {churn_rate:.2%}")

print(
    subs["subscription_status"].value_counts()
)
"""
)

nb.write(NB_DIR / "01_data_generation.ipynb")


# ===========================================================================
# 02_data_cleaning.ipynb
# ===========================================================================
nb = NotebookBuilder()
nb.namespace["ROOT"] = ROOT
nb.namespace["run_script"] = run_script
nb.markdown(
"""# 02 — Data Cleaning

Runs the full cleaning pipeline (`src/clean_data.py`) against the raw data
and inspects the before/after state of each table plus the generated
**Data Quality Report**.
"""
)

nb.code(
"""
result = run_script("clean_data.py")

if result.returncode != 0:
    print("Data cleaning failed.")
"""
)

nb.markdown("## Before vs after: row counts")

nb.code(
"""
import pandas as pd

RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

names = [
    "customers",
    "subscriptions",
    "transactions",
    "customer_activity",
    "support_tickets"
]

rows = []

for n in names:

    raw_n = len(
        pd.read_csv(RAW / f"{n}.csv")
    )

    clean_n = len(
        pd.read_csv(PROCESSED / f"{n}.csv")
    )

    rows.append(
        {
            "table": n,
            "raw_rows": raw_n,
            "processed_rows": clean_n,
            "removed": raw_n - clean_n
        }
    )

comparison = pd.DataFrame(rows)

print(
    comparison.to_string(index=False)
)
"""
)

nb.markdown("## Data Quality Report preview")

nb.code(
"""
report_path = ROOT / "reports" / "data_quality_report.md"

report_text = report_path.read_text(
    encoding="utf-8"
)

print(report_text[:3500])
"""
)

nb.markdown(
"## Sanity check: no more invalid values after cleaning"
)

nb.code(
"""
customers = pd.read_csv(
    PROCESSED / "customers.csv"
)

subs = pd.read_csv(
    PROCESSED / "subscriptions.csv"
)

print(
    "Duplicate customer_id after cleaning:",
    customers["customer_id"].duplicated().sum()
)

print(
    "Ages out of range after cleaning:",
    (
        (customers["age"] < 13)
        |
        (customers["age"] > 100)
    ).sum()
)

print(
    "Cancelled subs missing cancellation_date:",
    (
        (subs["subscription_status"] == "Cancelled")
        &
        (subs["cancellation_date"].isna())
    ).sum()
)

print(
    "Subscription status distinct values:",
    subs["subscription_status"].unique()
)
"""
)

nb.write(
    NB_DIR / "02_data_cleaning.ipynb"
)


# ===========================================================================
# 03_exploratory_analysis.ipynb
# ===========================================================================
nb = NotebookBuilder()
nb.namespace["ROOT"] = ROOT
nb.namespace["run_script"] = run_script

nb.markdown(
"""# 03 — Exploratory Data Analysis

Runs `src/eda.py` to produce the core business-question-driven charts.

All figures are saved to `outputs/figures/` for use in the README and
Power BI dashboard.
"""
)

nb.code(
"""
result = run_script("eda.py")

if result.returncode != 0:
    print("EDA failed.")
"""
)

nb.markdown(
"## Load processed data for inline analysis"
)

nb.code(
"""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_style("whitegrid")

PROCESSED = ROOT / "data" / "processed"

customers = pd.read_csv(
    PROCESSED / "customers.csv",
    parse_dates=["signup_date"]
)

subscriptions = pd.read_csv(
    PROCESSED / "subscriptions.csv",
    parse_dates=[
        "start_date",
        "end_date",
        "cancellation_date"
    ]
)

transactions = pd.read_csv(
    PROCESSED / "transactions.csv",
    parse_dates=["transaction_date"]
)

plans = pd.read_csv(
    PROCESSED / "plans.csv"
)

latest_sub = (
    subscriptions
    .sort_values("start_date")
    .groupby("customer_id")
    .last()
    .reset_index()
)

cust = customers.merge(
    latest_sub[
        [
            "customer_id",
            "plan_id",
            "billing_cycle",
            "subscription_status"
        ]
    ],
    on="customer_id"
)

cust = cust.merge(
    plans[
        [
            "plan_id",
            "plan_name"
        ]
    ],
    on="plan_id"
)

print(
    f"customers: {len(customers):,} | "
    f"subscriptions: {len(subscriptions):,} | "
    f"transactions: {len(transactions):,}"
)

print(
    f"Overall churn rate: "
    f"{(cust['subscription_status'] == 'Cancelled').mean():.2%}"
)
"""
)

nb.markdown("### Chart: Age distribution")

nb.code(
"""
fig, ax = plt.subplots(figsize=(7, 4.5))

sns.histplot(
    customers["age"],
    bins=30,
    ax=ax
)

ax.set_title(
    "Customer age distribution"
)

plt.show()
"""
)

nb.markdown(
"""**Takeaway:** The customer base skews toward working-age adults,
consistent with a mainstream consumer SaaS product."""
)

nb.markdown("### Chart: Churn rate by plan")

nb.code(
"""
churn_by_plan = (
    cust
    .groupby("plan_name")["subscription_status"]
    .apply(
        lambda s:
        (s == "Cancelled").mean() * 100
    )
    .sort_values(ascending=False)
)

fig, ax = plt.subplots(
    figsize=(6.5, 4.5)
)

sns.barplot(
    x=churn_by_plan.index,
    y=churn_by_plan.values,
    hue=churn_by_plan.index,
    legend=False,
    ax=ax
)

ax.set_ylabel(
    "Churn rate (%)"
)

ax.set_title(
    "Churn rate by plan"
)

for i, v in enumerate(
    churn_by_plan.values
):
    ax.text(
        i,
        v + 0.3,
        f"{v:.1f}%",
        ha="center"
    )

plt.show()

print(
    churn_by_plan.round(2)
)
"""
)

nb.markdown(
"""**Takeaway:** Entry-level plans churn noticeably more than
premium/enterprise plans."""
)

nb.markdown("### Chart: Monthly revenue trend")

nb.code(
"""
rev = transactions[
    (
        transactions["transaction_type"]
        == "Subscription Charge"
    )
    &
    (
        transactions["payment_status"]
        == "Success"
    )
]

monthly_rev = (
    rev
    .set_index("transaction_date")
    .resample("MS")["amount"]
    .sum()
)

fig, ax = plt.subplots(
    figsize=(9, 4.5)
)

ax.plot(
    monthly_rev.index,
    monthly_rev.values,
    marker="o"
)

ax.set_title(
    "Monthly subscription revenue"
)

ax.set_ylabel(
    "Revenue ($)"
)

plt.show()

print(
    f"Total revenue across the observation window: "
    f"${rev['amount'].sum():,.2f}"
)
"""
)

nb.markdown(
"""**Takeaway:** Revenue trends upward with the growing customer base,
although month-to-month growth is uneven."""
)

nb.markdown("### Chart: Churn by billing cycle")

nb.code(
"""
churn_by_billing = (
    cust
    .groupby("billing_cycle")["subscription_status"]
    .apply(
        lambda s:
        (s == "Cancelled").mean() * 100
    )
)

fig, ax = plt.subplots(
    figsize=(5.5, 4.5)
)

sns.barplot(
    x=churn_by_billing.index,
    y=churn_by_billing.values,
    hue=churn_by_billing.index,
    legend=False,
    ax=ax
)

ax.set_ylabel(
    "Churn rate (%)"
)

ax.set_title(
    "Churn rate: Monthly vs Annual billing"
)

plt.show()

print(
    churn_by_billing.round(2)
)
"""
)

nb.markdown(
"""**Takeaway:** Monthly-billed customers churn at a meaningfully
higher rate than annual subscribers."""
)

nb.markdown(
"""All 18 EDA figures, including the cohort heatmap, are saved under
`outputs/figures/`."""
)

nb.write(
    NB_DIR / "03_exploratory_analysis.ipynb"
)


# ===========================================================================
# 04_customer_segmentation.ipynb
# ===========================================================================

nb = NotebookBuilder()
nb.namespace["ROOT"] = ROOT
nb.namespace["run_script"] = run_script

nb.markdown(
"""# 04 — RFM Customer Segmentation

Computes Recency, Frequency, and Monetary scores for every customer and
assigns each to one of seven business segments:

- VIP
- Loyal
- Potential Loyal
- New
- At Risk
- Dormant
- Lost

Full logic lives in `src/segmentation.py`.
"""
)

nb.code(
"""
result = run_script("segmentation.py")

if result.returncode != 0:
    print("Segmentation failed.")
"""
)

nb.markdown(
"## Visualize segment sizes and revenue contribution"
)

nb.code(
"""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_style("whitegrid")

summary = pd.read_csv(
    ROOT / "outputs" / "tables" / "segment_summary.csv"
)

summary = summary.sort_values(
    "customers",
    ascending=False
)

print(
    summary.to_string(index=False)
)

fig, axes = plt.subplots(
    1,
    2,
    figsize=(13, 5)
)

sns.barplot(
    data=summary,
    x="segment",
    y="customers",
    hue="segment",
    legend=False,
    ax=axes[0]
)

axes[0].set_title(
    "Customers per RFM segment"
)

axes[0].tick_params(
    axis="x",
    rotation=30
)

sns.barplot(
    data=summary,
    x="segment",
    y="pct_of_revenue",
    hue="segment",
    legend=False,
    ax=axes[1]
)

axes[1].set_title(
    "% of total revenue per segment"
)

axes[1].tick_params(
    axis="x",
    rotation=30
)

plt.tight_layout()

plt.show()
"""
)

nb.markdown(
"### Segment churn rates"
)

nb.code(
"""
fig, ax = plt.subplots(
    figsize=(8, 4.5)
)

summary_sorted = summary.sort_values(
    "churn_rate",
    ascending=False
)

sns.barplot(
    data=summary_sorted,
    x="segment",
    y="churn_rate",
    hue="segment",
    legend=False,
    ax=ax
)

ax.set_ylabel(
    "Churn rate (%)"
)

ax.set_title(
    "Churn rate by RFM segment"
)

ax.tick_params(
    axis="x",
    rotation=30
)

plt.tight_layout()

plt.show()
"""
)

nb.markdown(
"""**Takeaway:** The `Lost` segment is churned by definition (100%).
`Loyal` and `Potential Loyal` customers represent meaningful retention
opportunities. RFM recency should be interpreted alongside billing cycle."""
)

nb.write(
    NB_DIR / "04_customer_segmentation.ipynb"
)


# ===========================================================================
# 05_churn_prediction.ipynb
# ===========================================================================

nb = NotebookBuilder()
nb.namespace["ROOT"] = ROOT
nb.namespace["run_script"] = run_script

nb.markdown(
"""# 05 — Churn Prediction

Trains Logistic Regression and Random Forest churn classifiers on a
leakage-safe feature table generated by `src/feature_engineering.py`.

The models are evaluated and every customer's churn probability and
revenue-at-risk score are generated.

**Leakage safety:** cancellation_date and cancellation_reason are excluded,
and behavioral features use records available by the customer's observation
cutoff.
"""
)

nb.code(
"""
result = run_script(
    "feature_engineering.py"
)

if result.returncode != 0:
    print(
        "Feature engineering failed."
    )
"""
)

nb.code(
"""
result = run_script(
    "churn_model.py"
)

if result.returncode != 0:
    print(
        "Churn model failed."
    )
"""
)

nb.markdown(
"## Inspect saved model outputs"
)

nb.code(
"""
import pandas as pd

comparison = pd.read_csv(
    ROOT
    / "outputs"
    / "model_results"
    / "model_comparison.csv"
)

print(
    comparison.to_string(index=False)
)
"""
)

nb.code(
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

roc_path = (
    ROOT
    / "outputs"
    / "figures"
    / "roc_curve.png"
)

importance_path = (
    ROOT
    / "outputs"
    / "figures"
    / "feature_importance.png"
)

fig, axes = plt.subplots(
    1,
    2,
    figsize=(14, 6)
)

axes[0].imshow(
    mpimg.imread(roc_path)
)

axes[0].axis("off")

axes[1].imshow(
    mpimg.imread(importance_path)
)

axes[1].axis("off")

plt.tight_layout()

plt.show()
"""
)

nb.markdown(
"""**Model choice:** Random Forest was selected based on higher ROC-AUC.
Because the business goal is to catch as many at-risk customers as possible,
recall on the churned class is particularly important."""
)

nb.markdown(
"## Revenue at risk & retention priority"
)

nb.code(
"""
priority = pd.read_csv(
    ROOT
    / "outputs"
    / "tables"
    / "retention_priority.csv"
)

print(
    priority[
        "retention_priority"
    ].value_counts()
)

print()

total_risk = (
    priority["annualized_revenue"]
    * priority["churn_probability"]
).sum()

print(
    "Total annualized revenue at risk "
    f"(Active customers, prob-weighted): "
    f"${total_risk:,.2f}"
)

print()

print(
    "Top 10 retention-priority customers:"
)

print(
    priority
    .sort_values(
        "churn_probability",
        ascending=False
    )
    .head(10)
    .to_string(index=False)
)
"""
)

nb.write(
    NB_DIR / "05_churn_prediction.ipynb"
)


# ===========================================================================
# COMPLETE
# ===========================================================================

print()
print("=" * 70)
print("All 5 notebooks built successfully.")
print("=" * 70)
print()
print(f"Project root : {ROOT}")
print(f"Notebook dir : {NB_DIR}")