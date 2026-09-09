"""
statistical_analysis.py
========================
Tests the statistical association between churn and key candidate drivers
using appropriate methods (t-test for continuous variables, chi-square for
categorical variables). Explicitly notes that association does not prove
causation.

Run:
    python src/statistical_analysis.py
Outputs:
    outputs/tables/statistical_tests.csv
"""
import numpy as np
import pandas as pd
from scipy import stats
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
TABLE_DIR = ROOT / "outputs" / "tables"


def load_data():
    customers = pd.read_csv(PROCESSED / "customers.csv", parse_dates=["signup_date"])
    subscriptions = pd.read_csv(PROCESSED / "subscriptions.csv",
                                 parse_dates=["start_date", "end_date", "cancellation_date"])
    activity = pd.read_csv(PROCESSED / "customer_activity.csv", parse_dates=["activity_date"])
    tickets = pd.read_csv(PROCESSED / "support_tickets.csv", parse_dates=["ticket_date"])

    latest_sub = subscriptions.sort_values("start_date").groupby("customer_id").last().reset_index()
    latest_sub["churn"] = (latest_sub["subscription_status"] == "Cancelled").astype(int)
    latest_sub["tenure_days"] = (latest_sub["cancellation_date"].fillna(pd.Timestamp("2025-09-01"))
                                  - latest_sub["start_date"]).dt.days

    eng = activity.groupby("customer_id")["sessions"].mean().rename("avg_sessions").reset_index()
    sat = tickets.groupby("customer_id")["satisfaction_score"].mean().rename("avg_satisfaction").reset_index()
    tix = tickets.groupby("customer_id").size().rename("n_tickets").reset_index()

    df = latest_sub.merge(customers[["customer_id", "age"]], on="customer_id", how="left")
    df = df.merge(eng, on="customer_id", how="left")
    df = df.merge(sat, on="customer_id", how="left")
    df = df.merge(tix, on="customer_id", how="left")
    df["n_tickets"] = df["n_tickets"].fillna(0)
    return df


def run_tests():
    df = load_data()
    results = []

    # --- t-tests: continuous variable, churned vs retained ---
    continuous_vars = {
        "tenure_days": "Tenure (days)",
        "monthly_price": "Monthly price",
        "avg_sessions": "Average sessions",
        "n_tickets": "Support ticket count",
        "avg_satisfaction": "Average satisfaction score",
    }
    for col, label in continuous_vars.items():
        churned = df.loc[df["churn"] == 1, col].dropna()
        retained = df.loc[df["churn"] == 0, col].dropna()
        t_stat, p_val = stats.ttest_ind(churned, retained, equal_var=False)
        results.append({
            "test": "Independent t-test", "variable": label,
            "churned_mean": round(churned.mean(), 2), "retained_mean": round(retained.mean(), 2),
            "statistic": round(t_stat, 3), "p_value": p_val,
            "significant_at_0.05": p_val < 0.05,
        })

    # --- chi-square tests: categorical variable vs churn ---
    categorical_vars = {
        "billing_cycle": "Billing cycle",
        "plan_id": "Plan",
    }
    for col, label in categorical_vars.items():
        ct = pd.crosstab(df[col], df["churn"])
        chi2, p_val, dof, _ = stats.chi2_contingency(ct)
        results.append({
            "test": "Chi-square test of independence", "variable": label,
            "churned_mean": np.nan, "retained_mean": np.nan,
            "statistic": round(chi2, 3), "p_value": p_val,
            "significant_at_0.05": p_val < 0.05,
        })

    # acquisition_channel (categorical, from customers)
    customers = pd.read_csv(PROCESSED / "customers.csv")
    df2 = df.merge(customers[["customer_id", "acquisition_channel"]], on="customer_id")
    ct = pd.crosstab(df2["acquisition_channel"], df2["churn"])
    chi2, p_val, dof, _ = stats.chi2_contingency(ct)
    results.append({
        "test": "Chi-square test of independence", "variable": "Acquisition channel",
        "churned_mean": np.nan, "retained_mean": np.nan,
        "statistic": round(chi2, 3), "p_value": p_val,
        "significant_at_0.05": p_val < 0.05,
    })

    # --- correlation: tenure vs churn probability (point-biserial) ---
    corr, p_val = stats.pointbiserialr(df["churn"], df["avg_sessions"].fillna(0))
    results.append({
        "test": "Point-biserial correlation", "variable": "Avg sessions vs churn",
        "churned_mean": np.nan, "retained_mean": np.nan,
        "statistic": round(corr, 3), "p_value": p_val,
        "significant_at_0.05": p_val < 0.05,
    })

    results_df = pd.DataFrame(results)
    results_df["p_value"] = results_df["p_value"].apply(lambda x: f"{x:.2e}" if x < 0.0001 else round(x, 5))
    return results_df


if __name__ == "__main__":
    results_df = run_tests()
    print(results_df.to_string(index=False))
    out_path = TABLE_DIR / "statistical_tests.csv"
    results_df.to_csv(out_path, index=False)
    print(f"\nSaved to {out_path}")
    print("\nNOTE: These tests establish statistical ASSOCIATION between each "
          "variable and churn in this observational dataset. They do not, on "
          "their own, establish CAUSATION. For example, low engagement and "
          "churn may both be driven by an unobserved third factor (e.g. a "
          "customer's declining need for the product).")
