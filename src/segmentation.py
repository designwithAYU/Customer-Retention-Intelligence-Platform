"""
segmentation.py
================
Computes RFM (Recency, Frequency, Monetary) scores for every customer and
assigns each to a business segment (VIP, Loyal, Potential Loyal, New,
At Risk, Dormant, Lost).

Run:
    python src/segmentation.py
Outputs:
    outputs/tables/customer_segments.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUT_TABLES = ROOT / "outputs" / "tables"
OUT_TABLES.mkdir(parents=True, exist_ok=True)
CUTOFF_DATE = pd.Timestamp("2025-09-01")


def compute_rfm():
    customers = pd.read_csv(PROCESSED / "customers.csv", parse_dates=["signup_date"])
    subscriptions = pd.read_csv(PROCESSED / "subscriptions.csv",
                                 parse_dates=["start_date", "end_date", "cancellation_date"])
    transactions = pd.read_csv(PROCESSED / "transactions.csv", parse_dates=["transaction_date"])

    latest_sub = (subscriptions.sort_values("start_date")
                  .groupby("customer_id").last().reset_index())

    txn = transactions[(transactions["transaction_type"] == "Subscription Charge") &
                        (transactions["payment_status"] == "Success")]
    rfm = txn.groupby("customer_id").agg(
        last_transaction_date=("transaction_date", "max"),
        frequency=("transaction_id", "count"),
        monetary=("amount", "sum"),
    ).reset_index()

    rfm["recency_days"] = (CUTOFF_DATE - rfm["last_transaction_date"]).dt.days

    rfm = rfm.merge(customers[["customer_id"]], on="customer_id", how="right")
    rfm["recency_days"] = rfm["recency_days"].fillna(9999)
    rfm["frequency"] = rfm["frequency"].fillna(0)
    rfm["monetary"] = rfm["monetary"].fillna(0)

    rfm = rfm.merge(latest_sub[["customer_id", "subscription_status"]], on="customer_id", how="left")

    # Score 1 (worst) - 5 (best) using quantiles. Lower recency = better -> reverse.
    rfm["R_score"] = pd.qcut(rfm["recency_days"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["F_score"] = pd.qcut(rfm["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["M_score"] = pd.qcut(rfm["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["rfm_score"] = rfm["R_score"] + rfm["F_score"] + rfm["M_score"]

    def assign_segment(row):
        r, f, m = row["R_score"], row["F_score"], row["M_score"]
        if row["subscription_status"] == "Cancelled" and r <= 2:
            return "Lost"
        if r <= 2 and (f <= 2 or m <= 2):
            return "Dormant"
        if r <= 2:
            return "At Risk"
        if r >= 4 and f >= 4 and m >= 4:
            return "VIP"
        if r >= 3 and f >= 3 and m >= 3:
            return "Loyal"
        if r >= 4 and f <= 2:
            return "New"
        return "Potential Loyal"

    rfm["segment"] = rfm.apply(assign_segment, axis=1)
    return rfm


if __name__ == "__main__":
    rfm = compute_rfm()

    summary = rfm.groupby("segment").agg(
        customers=("customer_id", "count"),
        total_revenue=("monetary", "sum"),
        churn_rate=("subscription_status", lambda s: (s == "Cancelled").mean()),
    ).reset_index().sort_values("total_revenue", ascending=False)
    summary["pct_of_customers"] = (100 * summary["customers"] / summary["customers"].sum()).round(2)
    summary["pct_of_revenue"] = (100 * summary["total_revenue"] / summary["total_revenue"].sum()).round(2)
    summary["churn_rate"] = (summary["churn_rate"] * 100).round(2)

    print("RFM Segment Summary:")
    print(summary.to_string(index=False))

    out_path = OUT_TABLES / "customer_segments.csv"
    rfm.to_csv(out_path, index=False)
    summary.to_csv(OUT_TABLES / "segment_summary.csv", index=False)
    print(f"\nSaved detailed segments to {out_path}")
    print(f"Saved segment summary to {OUT_TABLES / 'segment_summary.csv'}")
