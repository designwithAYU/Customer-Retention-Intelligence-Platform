"""
clean_data.py
=============
Loads the raw NovaStream datasets, inspects and fixes realistic data-quality
problems, and writes cleaned datasets to data/processed/. Also produces a
Data Quality Report (reports/data_quality_report.md) documenting every issue
found, how many records were affected, and how each was treated.

Run:
    python src/clean_data.py
"""

import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)
REPORTS = ROOT / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)

CUTOFF_DATE = pd.Timestamp("2025-09-01")

log = []  # collects (issue, records_affected, pct, treatment, reason)


def record(issue, n_affected, n_total, treatment, reason):
    pct = round(100 * n_affected / n_total, 3) if n_total else 0.0
    log.append((issue, n_affected, pct, treatment, reason))
    print(f"  [{issue}] affected={n_affected} ({pct}%) -> {treatment}")


print("Loading raw data...")
customers = pd.read_csv(RAW / "customers.csv", parse_dates=["signup_date"])
plans = pd.read_csv(RAW / "plans.csv")
subscriptions = pd.read_csv(RAW / "subscriptions.csv",
                             parse_dates=["start_date", "end_date", "cancellation_date"])
transactions = pd.read_csv(RAW / "transactions.csv", parse_dates=["transaction_date"])
customer_activity = pd.read_csv(RAW / "customer_activity.csv", parse_dates=["activity_date"])
support_tickets = pd.read_csv(RAW / "support_tickets.csv", parse_dates=["ticket_date"])
marketing_campaigns = pd.read_csv(RAW / "marketing_campaigns.csv", parse_dates=["campaign_date"])
interactions = pd.read_csv(RAW / "customer_campaign_interactions.csv", parse_dates=["interaction_date"])

print("\nRaw shapes:")
for name, df in [("customers", customers), ("subscriptions", subscriptions),
                  ("transactions", transactions), ("customer_activity", customer_activity),
                  ("support_tickets", support_tickets)]:
    print(f"  {name}: {df.shape}")

# ===========================================================================
# CUSTOMERS
# ===========================================================================
print("\n=== Cleaning customers ===")
n0 = len(customers)

# 1. Exact duplicate rows (double signup entries)
dupes = customers.duplicated(subset=["customer_id"], keep="first").sum()
customers = customers.drop_duplicates(subset=["customer_id"], keep="first")
record("Duplicate customers (duplicate customer_id)", dupes, n0, "Deduplicated (kept first occurrence)",
       "Simulated double-entry during signup; customer_id is the natural key")

# 2. Standardize categorical casing
n_country_upper = customers["country"].apply(lambda x: isinstance(x, str) and x.isupper()).sum()
customers["country"] = customers["country"].str.strip().str.title()
record("Inconsistent country capitalization", n_country_upper, len(customers),
       "Standardized to title case", "Source systems submitted country names in mixed case")

n_gender_lower = customers["gender"].apply(lambda x: isinstance(x, str) and x.islower()).sum()
customers["gender"] = customers["gender"].str.strip().str.title()
record("Inconsistent gender capitalization", n_gender_lower, len(customers),
       "Standardized to title case", "Manual data entry inconsistency")

# 3. Impossible ages -> treat as missing, then median-impute by region
invalid_age_mask = (customers["age"] < 13) | (customers["age"] > 100)
n_invalid_age = invalid_age_mask.sum()
customers.loc[invalid_age_mask, "age"] = np.nan
record("Invalid age (<13 or >100)", n_invalid_age, len(customers),
       "Converted to missing, then imputed", "Ages outside plausible human range are data entry errors")

# 4. Missing values
n_missing_age = customers["age"].isna().sum()
customers["age"] = customers["age"].fillna(customers.groupby("region")["age"].transform("median"))
customers["age"] = customers["age"].round().astype(int)
record("Missing age (incl. converted invalid ages)", n_missing_age, len(customers),
       "Median imputation by region", "Age is needed for demographic segmentation; region median is a reasonable proxy")

n_missing_gender = customers["gender"].isna().sum()
customers["gender"] = customers["gender"].fillna("Unknown")
record("Missing gender", n_missing_gender, len(customers),
       "Filled with 'Unknown' category", "Preserves the record without fabricating a gender")

n_missing_country = customers["country"].isna().sum()
customers["country"] = customers["country"].fillna("Unknown")
customers["region"] = customers["region"].fillna("Unknown")
record("Missing country/region", n_missing_country, len(customers),
       "Filled with 'Unknown' category", "Small share of records; dropping would lose otherwise valid revenue history")

n_missing_referral = customers["referral_source"].isna().sum()
customers["referral_source"] = customers["referral_source"].fillna("Not Captured")
record("Missing referral_source", n_missing_referral, len(customers),
       "Filled with 'Not Captured'", "Referral source is optional metadata, not critical to core analysis")

customers.to_csv(PROCESSED / "customers.csv", index=False)

# ===========================================================================
# PLANS
# ===========================================================================
plans.to_csv(PROCESSED / "plans.csv", index=False)

# ===========================================================================
# SUBSCRIPTIONS
# ===========================================================================
print("\n=== Cleaning subscriptions ===")
n0 = len(subscriptions)

# 1. Standardize status labels
bad_case_mask = subscriptions["subscription_status"].apply(lambda x: isinstance(x, str) and x.islower())
n_bad_case = bad_case_mask.sum()
subscriptions["subscription_status"] = subscriptions["subscription_status"].str.strip().str.title()
record("Inconsistent subscription_status labels (lowercase)", n_bad_case, n0,
       "Standardized to title case ('Active'/'Cancelled')", "Multiple source systems used different casing conventions")

# 2. Cancelled without cancellation_date -> flag and back-fill from end_date, else drop cancellation logic
missing_cancel_mask = (subscriptions["subscription_status"] == "Cancelled") & (subscriptions["cancellation_date"].isna())
n_missing_cancel = missing_cancel_mask.sum()
subscriptions.loc[missing_cancel_mask, "cancellation_date"] = subscriptions.loc[missing_cancel_mask, "end_date"]
still_missing = subscriptions["subscription_status"].eq("Cancelled") & subscriptions["cancellation_date"].isna()
subscriptions.loc[still_missing, "cancellation_date"] = CUTOFF_DATE
record("Cancelled subscriptions missing cancellation_date", n_missing_cancel, n0,
       "Back-filled from end_date, or set to observation cutoff if both missing",
       "Cancellation date is required for churn timing and cohort analysis")

# 3. Missing discount_percentage -> assume 0 (no discount on file)
n_missing_disc = subscriptions["discount_percentage"].isna().sum()
subscriptions["discount_percentage"] = subscriptions["discount_percentage"].fillna(0)
record("Missing discount_percentage", n_missing_disc, n0, "Filled with 0 (no discount)",
       "Absence of a discount record most plausibly means no discount was applied")

# 4. Validate dates: end_date/cancellation_date before start_date is invalid
invalid_date_mask = subscriptions["end_date"].notna() & (subscriptions["end_date"] < subscriptions["start_date"])
n_invalid_dates = invalid_date_mask.sum()
subscriptions.loc[invalid_date_mask, ["end_date", "cancellation_date"]] = pd.NaT
subscriptions.loc[invalid_date_mask, "subscription_status"] = "Active"
record("Invalid dates (end_date before start_date)", n_invalid_dates, n0,
       "Cleared end/cancellation date and reset status to Active",
       "A cancellation date earlier than signup is logically impossible")

subscriptions.to_csv(PROCESSED / "subscriptions.csv", index=False)
valid_subscription_ids = set(subscriptions["subscription_id"])
valid_customer_ids = set(customers["customer_id"])

# ===========================================================================
# TRANSACTIONS
# ===========================================================================
print("\n=== Cleaning transactions ===")
n0 = len(transactions)

# 1. Duplicate transactions (identical rows, e.g. from duplicate webhook events)
dupe_mask = transactions.duplicated(
    subset=["customer_id", "subscription_id", "transaction_date", "transaction_type", "amount"],
    keep="first"
)
n_dupe_txn = dupe_mask.sum()
transactions = transactions[~dupe_mask]
record("Duplicate transactions", n_dupe_txn, n0, "Removed duplicate rows",
       "Duplicate billing events caused by webhook/retry logic, not genuine repeat charges")

# 2. Orphan subscription_id (no matching subscription record)
orphan_mask = ~transactions["subscription_id"].isin(valid_subscription_ids)
n_orphan = orphan_mask.sum()
transactions = transactions[~orphan_mask]
record("Transactions with orphan subscription_id", n_orphan, n0, "Excluded",
       "Cannot be reliably attributed to a valid subscription; likely test/corrupted records")

# 3. Invalid negative charge amounts (Subscription Charge should not be negative unless Refunded)
n1 = len(transactions)
invalid_amt_mask = (transactions["transaction_type"] == "Subscription Charge") & \
                    (transactions["amount"] < 0) & (transactions["payment_status"] != "Refunded")
n_invalid_amt = invalid_amt_mask.sum()
transactions.loc[invalid_amt_mask, "amount"] = transactions.loc[invalid_amt_mask, "amount"].abs()
record("Invalid negative Subscription Charge amounts", n_invalid_amt, n1,
       "Converted to absolute value", "Negative charges (not refunds) indicate a sign error at the source system")

# 4. Missing payment_status
n_missing_ps = transactions["payment_status"].isna().sum()
transactions["payment_status"] = transactions["payment_status"].fillna("Unknown")
record("Missing payment_status", n_missing_ps, n1, "Filled with 'Unknown'",
       "Preserves the transaction record for revenue totals while flagging incomplete status data")

# 5. Orphan customer_id
n2 = len(transactions)
orphan_cust_mask = ~transactions["customer_id"].isin(valid_customer_ids)
n_orphan_cust = orphan_cust_mask.sum()
transactions = transactions[~orphan_cust_mask]
record("Transactions with orphan customer_id", n_orphan_cust, n2, "Excluded",
       "No matching customer record; cannot be attributed to a real customer")

transactions.to_csv(PROCESSED / "transactions.csv", index=False)

# ===========================================================================
# CUSTOMER ACTIVITY
# ===========================================================================
print("\n=== Cleaning customer_activity ===")
n0 = len(customer_activity)

n_missing_minutes = customer_activity["session_minutes"].isna().sum()
customer_activity["session_minutes"] = customer_activity["session_minutes"].fillna(
    customer_activity["session_minutes"].median()
)
record("Missing session_minutes", n_missing_minutes, n0, "Median imputation",
       "Small share of tracking-pixel failures; median avoids distorting engagement trend")

n_missing_feat = customer_activity["feature_usage_count"].isna().sum()
customer_activity["feature_usage_count"] = customer_activity["feature_usage_count"].fillna(0)
record("Missing feature_usage_count", n_missing_feat, n0, "Filled with 0",
       "Absence of a logged event most plausibly means no feature usage was recorded that period")

n_orphan_act = (~customer_activity["customer_id"].isin(valid_customer_ids)).sum()
customer_activity = customer_activity[customer_activity["customer_id"].isin(valid_customer_ids)]
record("Activity records with orphan customer_id", n_orphan_act, n0, "Excluded",
       "No matching customer record")

customer_activity.to_csv(PROCESSED / "customer_activity.csv", index=False)

# ===========================================================================
# SUPPORT TICKETS
# ===========================================================================
print("\n=== Cleaning support_tickets ===")
n0 = len(support_tickets)

case_mask = support_tickets["issue_type"].apply(lambda x: isinstance(x, str) and x.islower())
n_case = case_mask.sum()
support_tickets["issue_type"] = support_tickets["issue_type"].str.strip().str.title()
record("Inconsistent issue_type capitalization", n_case, n0, "Standardized to title case",
       "Ticketing system categories entered inconsistently by different support agents")

n_missing_sat = support_tickets["satisfaction_score"].isna().sum()
support_tickets["satisfaction_score"] = support_tickets["satisfaction_score"].fillna(
    support_tickets["satisfaction_score"].median()
)
record("Missing satisfaction_score", n_missing_sat, n0, "Median imputation",
       "Customers do not always complete post-ticket satisfaction surveys")

n_missing_res = support_tickets["resolution_time_hours"].isna().sum()
support_tickets["resolution_time_hours"] = support_tickets["resolution_time_hours"].fillna(
    support_tickets["resolution_time_hours"].median()
)
record("Missing resolution_time_hours", n_missing_res, n0, "Median imputation",
       "Open/in-progress tickets at time of export lack a final resolution time")

support_tickets.to_csv(PROCESSED / "support_tickets.csv", index=False)

# ===========================================================================
# MARKETING CAMPAIGNS + INTERACTIONS (clean pass-through, minimal issues)
# ===========================================================================
marketing_campaigns.to_csv(PROCESSED / "marketing_campaigns.csv", index=False)
n_orphan_int = (~interactions["customer_id"].isin(valid_customer_ids)).sum()
interactions = interactions[interactions["customer_id"].isin(valid_customer_ids)]
if n_orphan_int:
    record("Interactions with orphan customer_id", n_orphan_int, len(interactions) + n_orphan_int,
           "Excluded", "No matching customer record")
interactions.to_csv(PROCESSED / "customer_campaign_interactions.csv", index=False)

# ===========================================================================
# DATA QUALITY REPORT
# ===========================================================================
print("\nWriting data quality report...")
report_lines = [
    "# Data Quality Report",
    "",
    "**Project:** Customer Retention Intelligence Platform (NovaStream)",
    "",
    "This report documents every data quality issue discovered in the raw "
    "NovaStream datasets during the cleaning stage (`src/clean_data.py`), the "
    "number and percentage of records affected, the treatment applied, and the "
    "reasoning behind that treatment.",
    "",
    "| Issue | Records Affected | % Affected | Treatment | Reason |",
    "|---|---:|---:|---|---|",
]
for issue, n, pct, treatment, reason in log:
    report_lines.append(f"| {issue} | {n:,} | {pct}% | {treatment} | {reason} |")

report_lines += [
    "",
    "## Summary",
    f"- Total data quality checks performed: **{len(log)}**",
    f"- Total records affected across all checks: **{sum(x[1] for x in log):,}** "
    "(note: a single record can be affected by more than one issue, so this is "
    "not a unique-record count).",
    "",
    "## Assumptions & Limitations",
    "- Median imputation was used for numeric fields to limit the influence of outliers.",
    "- Categorical fields with missing values were filled with an explicit "
    "`Unknown` / `Not Captured` label rather than the mode, to avoid silently "
    "fabricating customer attributes.",
    "- Records that could not be attributed to a valid customer or subscription "
    "(orphan foreign keys) were excluded from the processed datasets, since "
    "they cannot be reliably analyzed.",
    "- All cleaning logic is deterministic and reproducible by re-running "
    "`src/clean_data.py` against `data/raw/`.",
]

(REPORTS / "data_quality_report.md").write_text("\n".join(report_lines))

print("\n=== CLEANING COMPLETE ===")
print("Processed shapes:")
for name, df in [("customers", customers), ("subscriptions", subscriptions),
                  ("transactions", transactions), ("customer_activity", customer_activity),
                  ("support_tickets", support_tickets), ("marketing_campaigns", marketing_campaigns),
                  ("customer_campaign_interactions", interactions)]:
    print(f"  {name}: {df.shape}")
print(f"\nData quality report written to: {REPORTS / 'data_quality_report.md'}")
