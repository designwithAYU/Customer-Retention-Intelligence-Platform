"""
feature_engineering.py
=======================
Builds a leakage-safe, customer-level feature table for churn prediction.

LEAKAGE SAFETY:
We deliberately EXCLUDE any information that is only known once (or after)
a customer has already churned:
    - cancellation_date
    - cancellation_reason
    - any activity/support records dated AFTER the customer's observation
      cutoff (see `as_of_date` logic below)

For churned customers, engagement/support features are computed using only
records up to (and including) their cancellation date -- exactly what would
have been known the day before they cancelled. For active customers, the
same features are computed using all records up to the global cutoff date.
This mirrors how a real-time churn model would be scored in production.
"""

import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
CUTOFF_DATE = pd.Timestamp("2025-09-01")


def build_feature_table():
    customers = pd.read_csv(PROCESSED / "customers.csv", parse_dates=["signup_date"])
    plans = pd.read_csv(PROCESSED / "plans.csv")
    subscriptions = pd.read_csv(PROCESSED / "subscriptions.csv",
                                 parse_dates=["start_date", "end_date", "cancellation_date"])
    transactions = pd.read_csv(PROCESSED / "transactions.csv", parse_dates=["transaction_date"])
    activity = pd.read_csv(PROCESSED / "customer_activity.csv", parse_dates=["activity_date"])
    tickets = pd.read_csv(PROCESSED / "support_tickets.csv", parse_dates=["ticket_date"])

    # Use each customer's FIRST subscription record to define their plan/billing
    # attributes and observation window (most customers have exactly one).
    first_sub = (subscriptions.sort_values("start_date")
                 .groupby("customer_id").first().reset_index())

    # Target: is this customer's most recent subscription Cancelled?
    latest_sub = (subscriptions.sort_values("start_date")
                  .groupby("customer_id").last().reset_index())
    target = latest_sub[["customer_id", "subscription_status"]].copy()
    target["churn"] = (target["subscription_status"] == "Cancelled").astype(int)

    # observation cutoff per customer: cancellation_date if churned, else global cutoff
    obs_cutoff = latest_sub[["customer_id"]].copy()
    obs_cutoff["as_of_date"] = np.where(
        latest_sub["subscription_status"] == "Cancelled",
        latest_sub["cancellation_date"],
        CUTOFF_DATE
    )
    obs_cutoff["as_of_date"] = pd.to_datetime(obs_cutoff["as_of_date"])

    df = customers.merge(first_sub[[
        "customer_id", "plan_id", "billing_cycle", "monthly_price",
        "discount_percentage", "start_date"
    ]], on="customer_id", how="inner")
    df = df.merge(plans[["plan_id", "plan_name", "plan_type", "premium_support"]], on="plan_id", how="left")
    df = df.merge(obs_cutoff, on="customer_id", how="left")
    df = df.merge(target[["customer_id", "churn"]], on="customer_id", how="left")

    df["tenure_days"] = (df["as_of_date"] - df["start_date"]).dt.days.clip(lower=1)
    df["tenure_months"] = (df["tenure_days"] / 30.44).round(1)

    # --- engagement features, computed only up to each customer's as_of_date ---
    activity_m = activity.merge(df[["customer_id", "as_of_date"]], on="customer_id", how="inner")
    activity_valid = activity_m[activity_m["activity_date"] <= activity_m["as_of_date"]]
    eng = activity_valid.groupby("customer_id").agg(
        avg_sessions=("sessions", "mean"),
        avg_session_minutes=("session_minutes", "mean"),
        avg_feature_usage=("feature_usage_count", "mean"),
        total_activity_periods=("activity_id", "count"),
        last_activity_date=("activity_date", "max"),
    ).reset_index()

    # recent vs prior engagement trend (last ~45 days vs the 45 days before that, relative to as_of_date)
    activity_valid = activity_valid.copy()
    activity_valid = activity_valid.merge(df[["customer_id", "as_of_date"]], on="customer_id", suffixes=("", "_y"))
    activity_valid["days_before_cutoff"] = (activity_valid["as_of_date"] - activity_valid["activity_date"]).dt.days
    recent = activity_valid[activity_valid["days_before_cutoff"] <= 45].groupby("customer_id")["sessions"].mean().rename("recent_avg_sessions")
    prior = activity_valid[(activity_valid["days_before_cutoff"] > 45) & (activity_valid["days_before_cutoff"] <= 90)].groupby("customer_id")["sessions"].mean().rename("prior_avg_sessions")
    trend = pd.concat([recent, prior], axis=1).reset_index()
    trend["engagement_trend_ratio"] = (trend["recent_avg_sessions"] / trend["prior_avg_sessions"].replace(0, np.nan))

    df = df.merge(eng, on="customer_id", how="left")
    df = df.merge(trend[["customer_id", "engagement_trend_ratio"]], on="customer_id", how="left")

    # --- support features, computed only up to each customer's as_of_date ---
    tickets_m = tickets.merge(df[["customer_id", "as_of_date"]], on="customer_id", how="inner")
    tickets_valid = tickets_m[tickets_m["ticket_date"] <= tickets_m["as_of_date"]]
    sup = tickets_valid.groupby("customer_id").agg(
        total_tickets=("ticket_id", "count"),
        avg_satisfaction=("satisfaction_score", "mean"),
        avg_resolution_time=("resolution_time_hours", "mean"),
        unresolved_tickets=("ticket_status", lambda s: (s == "Closed - Unresolved").sum()),
    ).reset_index()
    df = df.merge(sup, on="customer_id", how="left")

    # --- transaction / RFM-style features, computed only up to each customer's as_of_date ---
    txn = transactions[transactions["transaction_type"] == "Subscription Charge"]
    txn = txn[txn["payment_status"] == "Success"]
    txn_m = txn.merge(df[["customer_id", "as_of_date"]], on="customer_id", how="inner")
    txn_valid = txn_m[txn_m["transaction_date"] <= txn_m["as_of_date"]]
    rfm = txn_valid.groupby("customer_id").agg(
        total_revenue=("amount", "sum"),
        total_transactions=("amount", "count"),
        last_transaction_date=("transaction_date", "max"),
    ).reset_index()
    df = df.merge(rfm, on="customer_id", how="left")
    df["recency_days"] = (df["as_of_date"] - df["last_transaction_date"]).dt.days

    # fill sensible defaults for customers with no activity/tickets/transactions
    fill_zero = ["avg_sessions", "avg_session_minutes", "avg_feature_usage",
                 "total_activity_periods", "total_tickets", "unresolved_tickets",
                 "total_revenue", "total_transactions"]
    for c in fill_zero:
        df[c] = df[c].fillna(0)
    df["avg_satisfaction"] = df["avg_satisfaction"].fillna(df["avg_satisfaction"].median())
    df["avg_resolution_time"] = df["avg_resolution_time"].fillna(0)
    df["engagement_trend_ratio"] = df["engagement_trend_ratio"].fillna(1.0).clip(0, 5)
    df["recency_days"] = df["recency_days"].fillna(df["tenure_days"])

    feature_cols = [
        "customer_id", "age", "acquisition_channel", "plan_name", "billing_cycle",
        "monthly_price", "discount_percentage", "premium_support",
        "tenure_days", "tenure_months",
        "avg_sessions", "avg_session_minutes", "avg_feature_usage",
        "engagement_trend_ratio", "total_tickets", "avg_satisfaction",
        "avg_resolution_time", "unresolved_tickets", "total_revenue",
        "total_transactions", "recency_days", "churn",
    ]
    feature_table = df[feature_cols].copy()
    return feature_table


if __name__ == "__main__":
    ft = build_feature_table()
    out_path = PROCESSED / "feature_table.csv"
    ft.to_csv(out_path, index=False)
    print(f"Feature table built: {ft.shape}")
    print(f"Churn rate in feature table: {ft['churn'].mean():.4f}")
    print(f"Saved to {out_path}")
    print(ft.isna().sum()[ft.isna().sum() > 0])
