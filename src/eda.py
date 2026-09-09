"""
eda.py
======
Generates the core exploratory data analysis charts for the NovaStream
Customer Retention Intelligence Platform. Each chart is designed to answer a
specific business question (see inline comments).

Run:
    python src/eda.py
Outputs: outputs/figures/*.png
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

sns.set_style("whitegrid")
plt.rcParams["figure.facecolor"] = "white"

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
FIG_DIR = ROOT / "outputs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)
CUTOFF_DATE = pd.Timestamp("2025-09-01")

PALETTE = "viridis"


def load_all():
    customers = pd.read_csv(PROCESSED / "customers.csv", parse_dates=["signup_date"])
    plans = pd.read_csv(PROCESSED / "plans.csv")
    subscriptions = pd.read_csv(PROCESSED / "subscriptions.csv",
                                 parse_dates=["start_date", "end_date", "cancellation_date"])
    transactions = pd.read_csv(PROCESSED / "transactions.csv", parse_dates=["transaction_date"])
    activity = pd.read_csv(PROCESSED / "customer_activity.csv", parse_dates=["activity_date"])
    tickets = pd.read_csv(PROCESSED / "support_tickets.csv", parse_dates=["ticket_date"])
    return customers, plans, subscriptions, transactions, activity, tickets


def latest_subscription(subscriptions):
    return (subscriptions.sort_values("start_date").groupby("customer_id").last().reset_index())


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG_DIR / name, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {name}")


def run_eda():
    customers, plans, subscriptions, transactions, activity, tickets = load_all()
    latest_sub = latest_subscription(subscriptions)
    cust_full = customers.merge(latest_sub[["customer_id", "plan_id", "billing_cycle",
                                             "subscription_status"]], on="customer_id", how="left")
    cust_full = cust_full.merge(plans[["plan_id", "plan_name"]], on="plan_id", how="left")

    # 1. Age distribution --------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 4.5))
    sns.histplot(customers["age"], bins=30, color="#2E86AB", ax=ax)
    ax.set_title("Q: What does our customer age distribution look like?")
    ax.set_xlabel("Age"); ax.set_ylabel("Customers")
    save(fig, "01_age_distribution.png")

    # 2. Customer growth over time -------------------------------------
    growth = customers.set_index("signup_date").resample("MS").size().rename("new_customers").reset_index()
    growth["cumulative"] = growth["new_customers"].cumsum()
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax2 = ax.twinx()
    ax.bar(growth["signup_date"], growth["new_customers"], width=20, color="#A9D6E5", label="New customers")
    ax2.plot(growth["signup_date"], growth["cumulative"], color="#1B4965", linewidth=2.5, label="Cumulative")
    ax.set_title("Q: How fast is NovaStream growing its customer base?")
    ax.set_ylabel("New customers / month"); ax2.set_ylabel("Cumulative customers")
    fig.legend(loc="upper left", bbox_to_anchor=(0.1, 0.88))
    save(fig, "02_customer_growth.png")

    # 3. Monthly revenue trend ------------------------------------------
    rev = transactions[(transactions["transaction_type"] == "Subscription Charge") &
                        (transactions["payment_status"] == "Success")]
    monthly_rev = rev.set_index("transaction_date").resample("MS")["amount"].sum().reset_index()
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(monthly_rev["transaction_date"], monthly_rev["amount"], marker="o", color="#2E86AB")
    ax.set_title("Q: How has monthly subscription revenue trended?")
    ax.set_ylabel("Revenue ($)")
    save(fig, "03_monthly_revenue_trend.png")

    # 4. Plan distribution -------------------------------------------------
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    plan_counts = cust_full["plan_name"].value_counts()
    sns.barplot(x=plan_counts.index, y=plan_counts.values, hue=plan_counts.index,
                palette=PALETTE, legend=False, ax=ax)
    ax.set_title("Q: How are customers distributed across subscription plans?")
    ax.set_ylabel("Customers")
    save(fig, "04_plan_distribution.png")

    # 5. Acquisition channel mix -------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 4.5))
    chan_counts = customers["acquisition_channel"].value_counts()
    sns.barplot(y=chan_counts.index, x=chan_counts.values, hue=chan_counts.index,
                palette=PALETTE, legend=False, ax=ax)
    ax.set_title("Q: Which acquisition channels bring in the most customers?")
    ax.set_xlabel("Customers")
    save(fig, "05_acquisition_channel_mix.png")

    # 6. Churn rate by acquisition channel ----------------------------------
    churn_by_chan = cust_full.groupby("acquisition_channel")["subscription_status"].apply(
        lambda s: (s == "Cancelled").mean() * 100).sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.barplot(y=churn_by_chan.index, x=churn_by_chan.values, hue=churn_by_chan.index,
                palette="rocket", legend=False, ax=ax)
    ax.set_title("Q: Which acquisition channels bring the highest-churn customers?")
    ax.set_xlabel("Churn rate (%)")
    save(fig, "06_churn_by_acquisition_channel.png")

    # 7. Churn rate by plan ---------------------------------------------
    churn_by_plan = cust_full.groupby("plan_name")["subscription_status"].apply(
        lambda s: (s == "Cancelled").mean() * 100).sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    sns.barplot(x=churn_by_plan.index, y=churn_by_plan.values, hue=churn_by_plan.index,
                palette="rocket", legend=False, ax=ax)
    ax.set_title("Q: Which subscription plans have the highest churn?")
    ax.set_ylabel("Churn rate (%)")
    save(fig, "07_churn_by_plan.png")

    # 8. Churn rate: Monthly vs Annual billing ------------------------------
    churn_by_billing = cust_full.groupby("billing_cycle")["subscription_status"].apply(
        lambda s: (s == "Cancelled").mean() * 100)
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    sns.barplot(x=churn_by_billing.index, y=churn_by_billing.values, hue=churn_by_billing.index,
                palette=["#2E86AB", "#A23B72"], legend=False, ax=ax)
    ax.set_title("Q: Does billing cycle affect churn?")
    ax.set_ylabel("Churn rate (%)")
    save(fig, "08_churn_by_billing_cycle.png")

    # 9. Monthly churn trend -----------------------------------------------
    cancels = subscriptions[subscriptions["subscription_status"] == "Cancelled"].copy()
    cancels_by_month = cancels.set_index("cancellation_date").resample("MS").size()
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(cancels_by_month.index, cancels_by_month.values, marker="o", color="#A23B72")
    ax.set_title("Q: How has the volume of monthly cancellations trended?")
    ax.set_ylabel("Cancellations")
    save(fig, "09_monthly_churn_trend.png")

    # 10. Engagement: sessions distribution, active vs churned -------------
    avg_sessions = activity.groupby("customer_id")["sessions"].mean().rename("avg_sessions").reset_index()
    merged = avg_sessions.merge(cust_full[["customer_id", "subscription_status"]], on="customer_id")
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    sns.kdeplot(data=merged, x="avg_sessions", hue="subscription_status", fill=True,
                common_norm=False, palette={"Active": "#2E86AB", "Cancelled": "#A23B72"}, ax=ax)
    ax.set_title("Q: Do active and churned customers engage differently?")
    ax.set_xlabel("Average sessions per period")
    ax.set_xlim(0, merged["avg_sessions"].quantile(0.98))
    save(fig, "10_engagement_active_vs_churned.png")

    # 11. Support tickets vs churn ------------------------------------------
    tix_counts = tickets.groupby("customer_id").size().rename("n_tickets").reset_index()
    merged2 = cust_full[["customer_id", "subscription_status"]].merge(tix_counts, on="customer_id", how="left")
    merged2["n_tickets"] = merged2["n_tickets"].fillna(0)
    merged2["ticket_band"] = pd.cut(merged2["n_tickets"], [-1, 0, 2, 4, 100],
                                     labels=["0", "1-2", "3-4", "5+"])
    churn_by_tix = merged2.groupby("ticket_band", observed=True)["subscription_status"].apply(
        lambda s: (s == "Cancelled").mean() * 100)
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    sns.barplot(x=churn_by_tix.index, y=churn_by_tix.values, hue=churn_by_tix.index,
                palette="rocket", legend=False, ax=ax)
    ax.set_title("Q: Do customers with more support tickets churn more?")
    ax.set_xlabel("Support tickets filed"); ax.set_ylabel("Churn rate (%)")
    save(fig, "11_churn_by_support_tickets.png")

    # 12. Satisfaction score vs churn ---------------------------------------
    sat = tickets.groupby("customer_id")["satisfaction_score"].mean().rename("avg_satisfaction").reset_index()
    merged3 = cust_full[["customer_id", "subscription_status"]].merge(sat, on="customer_id")
    merged3["sat_band"] = pd.cut(merged3["avg_satisfaction"], [0, 2, 3, 4, 5],
                                  labels=["1-2", "2-3", "3-4", "4-5"])
    churn_by_sat = merged3.groupby("sat_band", observed=True)["subscription_status"].apply(
        lambda s: (s == "Cancelled").mean() * 100)
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    sns.barplot(x=churn_by_sat.index, y=churn_by_sat.values, hue=churn_by_sat.index,
                palette="rocket_r", legend=False, ax=ax)
    ax.set_title("Q: Does support satisfaction predict churn?")
    ax.set_xlabel("Average satisfaction score"); ax.set_ylabel("Churn rate (%)")
    save(fig, "12_churn_by_satisfaction.png")

    # 13. Tenure distribution of churned customers ---------------------------
    cancels["tenure_days"] = (cancels["cancellation_date"] - cancels["start_date"]).dt.days
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.histplot(cancels["tenure_days"], bins=40, color="#A23B72", ax=ax)
    ax.axvline(cancels["tenure_days"].median(), color="black", linestyle="--",
               label=f"Median = {cancels['tenure_days'].median():.0f} days")
    ax.set_title("Q: How long do customers typically stay before churning?")
    ax.set_xlabel("Tenure at cancellation (days)")
    ax.legend()
    save(fig, "13_tenure_at_churn.png")

    # 14. Revenue by region -------------------------------------------------
    rev_cust = rev.merge(customers[["customer_id", "region"]], on="customer_id")
    rev_by_region = rev_cust.groupby("region")["amount"].sum().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    sns.barplot(x=rev_by_region.index, y=rev_by_region.values, hue=rev_by_region.index,
                palette=PALETTE, legend=False, ax=ax)
    ax.set_title("Q: Which regions generate the most revenue?")
    ax.set_ylabel("Revenue ($)")
    save(fig, "14_revenue_by_region.png")

    # 15. Discount vs churn --------------------------------------------------
    latest_sub_disc = latest_sub.copy()
    latest_sub_disc["disc_band"] = pd.cut(latest_sub_disc["discount_percentage"],
                                           [-1, 0, 10, 20, 100], labels=["0%", "1-10%", "11-20%", "21%+"])
    churn_by_disc = latest_sub_disc.groupby("disc_band", observed=True)["subscription_status"].apply(
        lambda s: (s == "Cancelled").mean() * 100)
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    sns.barplot(x=churn_by_disc.index, y=churn_by_disc.values, hue=churn_by_disc.index,
                palette=PALETTE, legend=False, ax=ax)
    ax.set_title("Q: Do discounts reduce churn?")
    ax.set_xlabel("Discount tier"); ax.set_ylabel("Churn rate (%)")
    save(fig, "15_churn_by_discount.png")

    # 16. Feature usage vs churn (bonus chart) ------------------------------
    feat = activity.groupby("customer_id")["feature_usage_count"].mean().rename("avg_feature_usage").reset_index()
    merged4 = feat.merge(cust_full[["customer_id", "subscription_status"]], on="customer_id")
    fig, ax = plt.subplots(figsize=(7, 4.5))
    sns.boxplot(data=merged4, x="subscription_status", y="avg_feature_usage",
                hue="subscription_status", palette={"Active": "#2E86AB", "Cancelled": "#A23B72"},
                legend=False, ax=ax, showfliers=False)
    ax.set_title("Q: Do churned customers use fewer product features?")
    save(fig, "16_feature_usage_active_vs_churned.png")

    # 17. Age group vs churn (bonus chart) -----------------------------------
    cust_full["age_group"] = pd.cut(cust_full["age"], [0, 25, 35, 45, 60, 100],
                                     labels=["<25", "25-34", "35-44", "45-59", "60+"])
    churn_by_age = cust_full.groupby("age_group", observed=True)["subscription_status"].apply(
        lambda s: (s == "Cancelled").mean() * 100)
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    sns.barplot(x=churn_by_age.index, y=churn_by_age.values, hue=churn_by_age.index,
                palette=PALETTE, legend=False, ax=ax)
    ax.set_title("Q: Does age group relate to churn?")
    ax.set_xlabel("Age group"); ax.set_ylabel("Churn rate (%)")
    save(fig, "17_churn_by_age_group.png")

    print(f"\nEDA complete. {17} figures saved to {FIG_DIR}")


if __name__ == "__main__":
    run_eda()
