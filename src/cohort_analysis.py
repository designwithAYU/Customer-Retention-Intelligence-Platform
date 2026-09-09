"""
cohort_analysis.py
===================
Monthly cohort retention analysis. Cohort = signup month. Computes retention
at M0/M1/M2/M3/M6/M12 and renders a retention heatmap.

Run:
    python src/cohort_analysis.py
Outputs:
    outputs/tables/cohort_retention.csv
    outputs/figures/18_cohort_retention_heatmap.png
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
FIG_DIR = ROOT / "outputs" / "figures"
TABLE_DIR = ROOT / "outputs" / "tables"
CUTOFF_DATE = pd.Timestamp("2025-09-01")
MILESTONES = [0, 1, 2, 3, 6, 12]


def build_cohort_table():
    subscriptions = pd.read_csv(PROCESSED / "subscriptions.csv",
                                 parse_dates=["start_date", "end_date", "cancellation_date"])
    first_sub = subscriptions.sort_values("start_date").groupby("customer_id").first().reset_index()
    churn = subscriptions.groupby("customer_id").apply(
        lambda g: g.loc[g["subscription_status"] == "Cancelled", "cancellation_date"].min()
        if (g["subscription_status"] == "Cancelled").any() else pd.NaT,
        include_groups=False
    ).rename("churn_date").reset_index()

    base = first_sub[["customer_id", "start_date"]].merge(churn, on="customer_id", how="left")
    base["cohort_month"] = base["start_date"].dt.to_period("M").astype(str)

    rows = []
    for m in MILESTONES:
        milestone_date = base["start_date"] + pd.DateOffset(months=m)
        # only include cohorts old enough to have reached this milestone by the cutoff
        eligible = milestone_date <= CUTOFF_DATE
        retained = base["churn_date"].isna() | (base["churn_date"] >= milestone_date)
        tmp = base[eligible].copy()
        tmp["retained"] = retained[eligible]
        g = tmp.groupby("cohort_month").agg(cohort_size=("customer_id", "count"),
                                             retained=("retained", "sum")).reset_index()
        g["retention_pct"] = (100 * g["retained"] / g["cohort_size"]).round(1)
        g["milestone"] = f"M{m}"
        rows.append(g)

    long_table = pd.concat(rows, ignore_index=True)
    pivot = long_table.pivot(index="cohort_month", columns="milestone", values="retention_pct")
    pivot = pivot[[f"M{m}" for m in MILESTONES]]
    pivot = pivot.sort_index()
    return pivot, long_table


if __name__ == "__main__":
    pivot, long_table = build_cohort_table()
    pivot.to_csv(TABLE_DIR / "cohort_retention.csv")
    print("Cohort retention table (%):")
    print(pivot.to_string())

    fig, ax = plt.subplots(figsize=(8, 10))
    sns.heatmap(pivot, annot=True, fmt=".0f", cmap="YlGnBu", vmin=40, vmax=100,
                cbar_kws={"label": "Retention %"}, ax=ax)
    ax.set_title("Q: Are newer signup cohorts retaining better or worse than older ones?")
    ax.set_xlabel("Months since signup")
    ax.set_ylabel("Signup cohort (month)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "18_cohort_retention_heatmap.png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"\nSaved heatmap to {FIG_DIR / '18_cohort_retention_heatmap.png'}")

    # Trend check: compare average M3 retention of first-half vs second-half cohorts
    valid_m3 = pivot["M3"].dropna()
    half = len(valid_m3) // 2
    if half > 0:
        early = valid_m3.iloc[:half].mean()
        late = valid_m3.iloc[half:].mean()
        print(f"\nEarly cohorts avg M3 retention: {early:.1f}% | Later cohorts avg M3 retention: {late:.1f}%")
        trend = "improving" if late > early else "declining" if late < early else "flat"
        print(f"Cohort trend appears to be: {trend}")
