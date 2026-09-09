"""
generate_data.py
=================
Generates a realistic, messy, synthetic dataset for NovaStream, a fictional
subscription/SaaS company, to support the Customer Retention Intelligence
Platform portfolio project.

Design philosophy:
- Churn is driven by a latent, per-customer "risk" signal built from
  acquisition channel, plan, billing cycle, age, discount, and random
  customer-level frailty (unobserved heterogeneity) -- NOT a hardcoded
  lookup table. This produces noisy, believable, non-deterministic patterns.
- Engagement, satisfaction, and support-ticket behavior are correlated with
  the same latent risk (plus independent noise) so that EDA discovers
  believable relationships rather than manufactured ones.
- Data quality problems (missing values, duplicates, bad types, orphan
  records, inconsistent labels) are injected intentionally AFTER the "clean"
  data is generated, and are only fixed later in the cleaning stage.

Run:
    python src/generate_data.py
Outputs raw CSVs to data/raw/
"""

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import timedelta

RNG_SEED = 42
rng = np.random.default_rng(RNG_SEED)

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
N_CUSTOMERS = 52_000
DATA_START = pd.Timestamp("2023-09-01")
DATA_END = pd.Timestamp("2025-08-31")      # last possible signup date
CUTOFF_DATE = pd.Timestamp("2025-09-01")   # "as of" date for the whole dataset
MAX_TENURE_MONTHS = 24

COUNTRIES = {
    "United States": "North America", "Canada": "North America",
    "United Kingdom": "Europe", "Germany": "Europe", "France": "Europe",
    "Spain": "Europe", "Netherlands": "Europe",
    "India": "Asia Pacific", "Australia": "Asia Pacific", "Singapore": "Asia Pacific",
    "Japan": "Asia Pacific", "Brazil": "Latin America", "Mexico": "Latin America",
}
COUNTRY_LIST = list(COUNTRIES.keys())
COUNTRY_WEIGHTS = np.array([18, 6, 10, 8, 7, 5, 4, 12, 6, 4, 5, 8, 7], dtype=float)
COUNTRY_WEIGHTS /= COUNTRY_WEIGHTS.sum()

CHANNELS = ["Organic Search", "Paid Search", "Social Media", "Referral",
            "Affiliate", "Email Marketing", "Direct"]
CHANNEL_WEIGHTS = np.array([20, 18, 16, 14, 10, 12, 10], dtype=float)
CHANNEL_WEIGHTS /= CHANNEL_WEIGHTS.sum()
# relative churn-risk multiplier per channel (referral/organic = stickier customers)
CHANNEL_RISK = {
    "Organic Search": -0.15, "Paid Search": 0.20, "Social Media": 0.25,
    "Referral": -0.35, "Affiliate": 0.10, "Email Marketing": 0.00, "Direct": -0.05,
}
# relative customer-value multiplier per channel (referral/organic bring higher LTV;
# paid search can bring high volume but not necessarily high value)
CHANNEL_VALUE = {
    "Organic Search": 0.05, "Paid Search": -0.05, "Social Media": -0.10,
    "Referral": 0.20, "Affiliate": -0.10, "Email Marketing": 0.00, "Direct": 0.10,
}

REFERRAL_SOURCES = ["Friend/Family", "Colleague", "Influencer", "Online Ad",
                    "Search Engine", "App Store", "Blog/Review Site", "Other"]

PLANS = pd.DataFrame([
    {"plan_id": 1, "plan_name": "Basic", "plan_type": "Individual", "monthly_price": 9.99, "max_devices": 1, "premium_support": 0},
    {"plan_id": 2, "plan_name": "Standard", "plan_type": "Individual", "monthly_price": 15.99, "max_devices": 2, "premium_support": 0},
    {"plan_id": 3, "plan_name": "Premium", "plan_type": "Family", "monthly_price": 24.99, "max_devices": 5, "premium_support": 1},
    {"plan_id": 4, "plan_name": "Enterprise", "plan_type": "Team", "monthly_price": 49.99, "max_devices": 20, "premium_support": 1},
])
PLAN_WEIGHTS = np.array([35, 30, 22, 13], dtype=float)
PLAN_WEIGHTS /= PLAN_WEIGHTS.sum()
# relative churn-risk multiplier per plan (basic = higher risk, enterprise = stickier)
PLAN_RISK = {1: 0.30, 2: 0.10, 3: -0.10, 4: -0.30}

CANCEL_REASONS = ["Too expensive", "Found alternative", "Not using enough",
                  "Missing features", "Poor customer service", "Technical issues",
                  "Moving/life change", "No reason given"]

ISSUE_TYPES = ["Billing", "Technical", "Account Access", "Feature Request",
               "Content Issue", "Cancellation Request", "General Inquiry"]

print("Step 1/8: Generating customers...")
# ---------------------------------------------------------------------------
# CUSTOMERS
# ---------------------------------------------------------------------------
customer_id = np.arange(1, N_CUSTOMERS + 1)

# signup dates: slight upward growth trend over the 24 months
days_range = (DATA_END - DATA_START).days
growth_weights = np.linspace(0.7, 1.3, days_range + 1)
growth_weights /= growth_weights.sum()
signup_offsets = rng.choice(days_range + 1, size=N_CUSTOMERS, p=growth_weights)
signup_date = DATA_START + pd.to_timedelta(signup_offsets, unit="D")

gender = rng.choice(["Male", "Female", "Non-binary"], size=N_CUSTOMERS, p=[0.48, 0.48, 0.04])
age = rng.normal(38, 12, size=N_CUSTOMERS).round().astype(int)
age = np.clip(age, 18, 85)

country = rng.choice(COUNTRY_LIST, size=N_CUSTOMERS, p=COUNTRY_WEIGHTS)
region = np.array([COUNTRIES[c] for c in country])

acquisition_channel = rng.choice(CHANNELS, size=N_CUSTOMERS, p=CHANNEL_WEIGHTS)
referral_source = rng.choice(REFERRAL_SOURCES, size=N_CUSTOMERS)

customers = pd.DataFrame({
    "customer_id": customer_id,
    "signup_date": signup_date,
    "gender": gender,
    "age": age,
    "country": country,
    "region": region,
    "acquisition_channel": acquisition_channel,
    "referral_source": referral_source,
})

print("Step 2/8: Assigning plans & simulating churn (latent-risk survival model)...")
# ---------------------------------------------------------------------------
# LATENT RISK / CHURN PROPENSITY
# ---------------------------------------------------------------------------
plan_id = rng.choice(PLANS["plan_id"].values, size=N_CUSTOMERS, p=PLAN_WEIGHTS)
billing_cycle = rng.choice(["Monthly", "Annual"], size=N_CUSTOMERS, p=[0.68, 0.32])
discount_pct = rng.choice([0, 0, 0, 10, 15, 20, 30], size=N_CUSTOMERS)

plan_price_map = PLANS.set_index("plan_id")["monthly_price"].to_dict()
base_price = np.array([plan_price_map[p] for p in plan_id])
monthly_price = np.round(base_price * (1 - discount_pct / 100), 2)

# customer-level frailty (unobserved heterogeneity) -- pure noise
frailty = rng.normal(0, 0.55, size=N_CUSTOMERS)

channel_risk = np.array([CHANNEL_RISK[c] for c in acquisition_channel])
plan_risk = np.array([PLAN_RISK[p] for p in plan_id])
billing_risk = np.where(billing_cycle == "Monthly", 0.30, -0.30)
age_risk = (35 - age) / 100.0            # younger -> slightly higher risk
discount_risk = -discount_pct / 200.0     # discounts modestly reduce churn

latent_risk = (channel_risk + plan_risk + billing_risk + age_risk
               + discount_risk + frailty)

# convert to a baseline monthly hazard via logistic squashing, centered
# around ~1.8% baseline monthly hazard (typical SaaS-like monthly churn)
base_hazard = 1 / (1 + np.exp(-(latent_risk - 4.0)))
base_hazard = np.clip(base_hazard, 0.001, 0.22)

max_tenure = ((CUTOFF_DATE - signup_date) / np.timedelta64(1, "D") / 30.44).astype(int)
max_tenure = np.clip(max_tenure, 1, MAX_TENURE_MONTHS)

churn_month = np.full(N_CUSTOMERS, -1)         # -1 = still active (censored)
still_active = np.ones(N_CUSTOMERS, dtype=bool)

for t in range(1, MAX_TENURE_MONTHS + 1):
    eligible = still_active & (max_tenure >= t)
    if not eligible.any():
        continue
    # time-varying multiplier: elevated onboarding risk, then loyalty discount
    if t <= 2:
        mult = 1.7
    elif t <= 11:
        mult = 1.0
    else:
        mult = 0.65
    hz = np.clip(base_hazard[eligible] * mult, 0, 0.9)
    draws = rng.random(eligible.sum())
    churned_now = draws < hz
    idx = np.where(eligible)[0][churned_now]
    churn_month[idx] = t
    still_active[idx] = False

subscription_status = np.where(churn_month == -1, "Active", "Cancelled")
cancellation_date = np.where(
    churn_month == -1, np.datetime64("NaT"),
    (signup_date + pd.to_timedelta((churn_month * 30.44).round(), unit="D")).where(churn_month != -1)
)
cancellation_date = pd.to_datetime(pd.Series(cancellation_date))
# clip cancellation date so it never exceeds the observation cutoff
cancellation_date = cancellation_date.clip(upper=CUTOFF_DATE)

cancellation_reason = np.where(
    subscription_status == "Cancelled",
    rng.choice(CANCEL_REASONS, size=N_CUSTOMERS),
    None
)

subscriptions = pd.DataFrame({
    "subscription_id": np.arange(1, N_CUSTOMERS + 1),
    "customer_id": customer_id,
    "plan_id": plan_id,
    "start_date": signup_date,
    "end_date": cancellation_date,
    "billing_cycle": billing_cycle,
    "monthly_price": monthly_price,
    "discount_percentage": discount_pct,
    "subscription_status": subscription_status,
    "cancellation_date": cancellation_date,
    "cancellation_reason": cancellation_reason,
})

# ---- reactivations: ~7% of churned customers resubscribe later on a new plan
print("Step 3/8: Simulating reactivations (repeat subscriptions)...")
churned_mask = subscription_status == "Cancelled"
churned_idx = np.where(churned_mask)[0]
reactivate_idx = rng.choice(churned_idx, size=int(len(churned_idx) * 0.07), replace=False)

reactivations = []
next_sub_id = subscriptions["subscription_id"].max() + 1
for i in reactivate_idx:
    cancel_dt = cancellation_date.iloc[i]
    if pd.isna(cancel_dt):
        continue
    gap_days = int(rng.integers(20, 200))
    new_start = cancel_dt + timedelta(days=gap_days)
    if new_start >= CUTOFF_DATE:
        continue
    new_plan = rng.choice(PLANS["plan_id"].values, p=PLAN_WEIGHTS)
    new_billing = rng.choice(["Monthly", "Annual"], p=[0.68, 0.32])
    new_discount = rng.choice([0, 0, 10, 15, 20])
    new_price = round(plan_price_map[new_plan] * (1 - new_discount / 100), 2)
    remaining_months = max(1, int((CUTOFF_DATE - new_start).days / 30.44))
    # simple re-churn hazard, slightly elevated (serial churners)
    re_hazard = np.clip(base_hazard[i] * 1.15, 0.01, 0.4)
    re_churn_month = -1
    for t in range(1, remaining_months + 1):
        if rng.random() < re_hazard:
            re_churn_month = t
            break
    if re_churn_month == -1:
        re_status, re_end, re_reason = "Active", pd.NaT, None
    else:
        re_status = "Cancelled"
        re_end = new_start + timedelta(days=int(re_churn_month * 30.44))
        re_end = min(re_end, CUTOFF_DATE)
        re_reason = rng.choice(CANCEL_REASONS)
    reactivations.append({
        "subscription_id": next_sub_id,
        "customer_id": customer_id[i],
        "plan_id": new_plan,
        "start_date": new_start,
        "end_date": re_end,
        "billing_cycle": new_billing,
        "monthly_price": new_price,
        "discount_percentage": new_discount,
        "subscription_status": re_status,
        "cancellation_date": re_end,
        "cancellation_reason": re_reason,
    })
    next_sub_id += 1

subscriptions = pd.concat([subscriptions, pd.DataFrame(reactivations)], ignore_index=True)

print(f"  customers: {len(customers):,} | subscriptions: {len(subscriptions):,}")

# ---------------------------------------------------------------------------
# TRANSACTIONS (billing events across the life of each subscription)
# ---------------------------------------------------------------------------
print("Step 4/8: Generating transactions...")
txn_rows = []
txn_id = 1
sub_records = subscriptions.to_dict("records")

for s in sub_records:
    start = s["start_date"]
    end = s["end_date"] if pd.notna(s["end_date"]) else CUTOFF_DATE
    cycle_days = 30 if s["billing_cycle"] == "Monthly" else 365
    price = s["monthly_price"] if s["billing_cycle"] == "Monthly" else round(s["monthly_price"] * 12 * 0.90, 2)  # ~10% annual discount baked in
    current = start
    while current <= end:
        # occasional failed payment (more likely for higher-risk/monthly customers)
        payment_status = rng.choice(["Success", "Failed", "Refunded"], p=[0.94, 0.045, 0.015])
        amount = price if payment_status != "Refunded" else -price
        discount_amt = round(price * (s["discount_percentage"] / 100) / (1 - s["discount_percentage"] / 100), 2) if s["discount_percentage"] else 0.0
        txn_rows.append((
            txn_id, s["customer_id"], s["subscription_id"], current,
            "Subscription Charge", round(amount, 2), discount_amt, payment_status
        ))
        txn_id += 1
        current = current + timedelta(days=cycle_days)

    # occasional one-off add-on purchases
    n_addons = rng.poisson(0.6)
    for _ in range(n_addons):
        addon_date = start + timedelta(days=int(rng.integers(0, max(1, (end - start).days + 1))))
        if addon_date > CUTOFF_DATE:
            continue
        txn_rows.append((
            txn_id, s["customer_id"], s["subscription_id"], addon_date,
            "Add-on Purchase", round(rng.uniform(2, 25), 2), 0.0, "Success"
        ))
        txn_id += 1

transactions = pd.DataFrame(txn_rows, columns=[
    "transaction_id", "customer_id", "subscription_id", "transaction_date",
    "transaction_type", "amount", "discount_amount", "payment_status"
])
print(f"  transactions: {len(transactions):,}")

# ---------------------------------------------------------------------------
# CUSTOMER ACTIVITY (monthly engagement snapshots, with pre-churn decline)
# ---------------------------------------------------------------------------
print("Step 5/8: Generating customer activity records...")
cust_lookup = customers.set_index("customer_id")
sub_by_cust = subscriptions.sort_values("start_date").groupby("customer_id").first()

activity_rows = []
activity_id = 1
for cust in sub_records:
    cid = cust["customer_id"]
    start = cust["start_date"]
    end = cust["end_date"] if pd.notna(cust["end_date"]) else CUTOFF_DATE
    # bi-weekly (every ~15 days) activity snapshots for finer-grained engagement history
    n_periods = max(1, int((end - start).days / 15.2) + 1)
    base_engagement = np.clip(rng.normal(7, 3), 0.5, 22)  # base sessions per ~2 weeks
    is_churned = cust["subscription_status"] == "Cancelled"
    # Not every churner shows a visible engagement decline before leaving --
    # some cancel abruptly (price shock, one-off bad experience, competitor
    # switch) with no warning signs. Only a majority, not all, decline.
    will_show_decline = is_churned and (rng.random() < 0.62)
    decline_strength = rng.uniform(0.35, 0.75)  # how deep the dip goes, per customer

    period_cursor = start
    for m in range(n_periods):
        decline_factor = 1.0
        if will_show_decline and m >= n_periods - 5:
            # engagement erodes, to a customer-specific degree, in the final
            # ~2.5 months (5 periods) before cancellation
            steps_from_end = n_periods - m
            decline_factor = 1 - (1 - decline_strength) * (steps_from_end / 5)
        noise = rng.normal(1.0, 0.45)
        sessions = max(0, round(base_engagement * decline_factor * noise))
        session_minutes = max(0, round(sessions * rng.uniform(8, 22)))
        content_consumed = max(0, round(sessions * rng.uniform(0.6, 1.4)))
        feature_usage = max(0, round(sessions * rng.uniform(0.2, 0.8)))
        activity_rows.append((
            activity_id, cid, period_cursor, sessions, session_minutes,
            content_consumed, feature_usage
        ))
        activity_id += 1
        period_cursor = period_cursor + timedelta(days=15)
        if period_cursor > CUTOFF_DATE:
            break

customer_activity = pd.DataFrame(activity_rows, columns=[
    "activity_id", "customer_id", "activity_date", "sessions", "session_minutes",
    "content_consumed", "feature_usage_count"
])
print(f"  customer_activity: {len(customer_activity):,}")

# ---------------------------------------------------------------------------
# SUPPORT TICKETS (higher-risk customers file more / less-resolved tickets)
# ---------------------------------------------------------------------------
print("Step 6/8: Generating support tickets...")
ticket_rows = []
ticket_id = 1
risk_pct = pd.Series(base_hazard).rank(pct=True).values  # 0..1 percentile of risk
for i, cust in enumerate(sub_records[:N_CUSTOMERS]):
    cid = cust["customer_id"]
    start = cust["start_date"]
    end = cust["end_date"] if pd.notna(cust["end_date"]) else CUTOFF_DATE
    tenure_days = max(1, (end - start).days)
    expected_tickets = 0.4 + risk_pct[i] * 2.2  # higher risk -> more tickets on average
    n_tickets = rng.poisson(expected_tickets)
    for _ in range(n_tickets):
        t_date = start + timedelta(days=int(rng.integers(0, tenure_days + 1)))
        if t_date > CUTOFF_DATE:
            continue
        issue = rng.choice(ISSUE_TYPES)
        # higher risk customers get worse resolution & satisfaction, with noise
        resolution_time = max(0.5, round(rng.gamma(2.0, 6 + risk_pct[i] * 10), 1))
        satisfaction = int(np.clip(round(rng.normal(4.0 - risk_pct[i] * 2.0, 1.0)), 1, 5))
        status = rng.choice(["Resolved", "Resolved", "Resolved", "Escalated", "Closed - Unresolved"])
        ticket_rows.append((
            ticket_id, cid, t_date, issue, resolution_time, satisfaction, status
        ))
        ticket_id += 1

support_tickets = pd.DataFrame(ticket_rows, columns=[
    "ticket_id", "customer_id", "ticket_date", "issue_type",
    "resolution_time_hours", "satisfaction_score", "ticket_status"
])
print(f"  support_tickets: {len(support_tickets):,}")

# ---------------------------------------------------------------------------
# MARKETING CAMPAIGNS + INTERACTIONS
# ---------------------------------------------------------------------------
print("Step 7/8: Generating marketing campaigns & interactions...")
n_campaigns = 180
campaign_dates = DATA_START + pd.to_timedelta(
    rng.integers(0, days_range, size=n_campaigns), unit="D"
)
campaign_channel = rng.choice(CHANNELS, size=n_campaigns, p=CHANNEL_WEIGHTS)
campaign_type = rng.choice(
    ["Awareness", "Promotion", "Retargeting", "Retention", "Referral Bonus"],
    size=n_campaigns
)
campaign_spend = np.round(rng.gamma(3.0, 1500, size=n_campaigns), 2)

marketing_campaigns = pd.DataFrame({
    "campaign_id": np.arange(1, n_campaigns + 1),
    "campaign_date": campaign_dates,
    "channel": campaign_channel,
    "campaign_type": campaign_type,
    "spend": campaign_spend,
})

interaction_rows = []
interaction_id = 1
campaigns_by_channel = marketing_campaigns.groupby("channel")["campaign_id"].apply(list).to_dict()
for i, cust in enumerate(sub_records[:N_CUSTOMERS]):
    cid = cust["customer_id"]
    chan = customers.loc[customers["customer_id"] == cid, "acquisition_channel"].values
    chan = chan[0] if len(chan) else rng.choice(CHANNELS)
    candidate_campaigns = campaigns_by_channel.get(chan, marketing_campaigns["campaign_id"].tolist())
    n_interactions = rng.poisson(2.0)
    for _ in range(n_interactions):
        camp_id = rng.choice(candidate_campaigns)
        camp_date = marketing_campaigns.loc[marketing_campaigns["campaign_id"] == camp_id, "campaign_date"].values[0]
        interact_date = pd.Timestamp(camp_date) + timedelta(days=int(rng.integers(0, 14)))
        interaction_type = rng.choice(["Email Open", "Click", "Ad View", "Conversion", "Unsubscribe"],
                                       p=[0.35, 0.25, 0.25, 0.10, 0.05])
        interaction_rows.append((interaction_id, cid, camp_id, interaction_type, interact_date))
        interaction_id += 1

customer_campaign_interactions = pd.DataFrame(interaction_rows, columns=[
    "interaction_id", "customer_id", "campaign_id", "interaction_type", "interaction_date"
])
print(f"  marketing_campaigns: {len(marketing_campaigns):,} | interactions: {len(customer_campaign_interactions):,}")

# ---------------------------------------------------------------------------
# STEP 8: INJECT REALISTIC DATA QUALITY PROBLEMS (raw, uncleaned data)
# ---------------------------------------------------------------------------
print("Step 8/8: Injecting realistic data quality issues...")

def inject_missing(df, cols, frac=0.02):
    df = df.copy()
    for c in cols:
        mask = rng.random(len(df)) < frac
        df.loc[mask, c] = np.nan
    return df

# customers: missing age/gender/country, impossible ages, inconsistent casing
customers_raw = customers.copy()
customers_raw = inject_missing(customers_raw, ["age", "gender", "country", "referral_source"], frac=0.02)
bad_age_idx = rng.choice(customers_raw.index, size=int(0.005 * len(customers_raw)), replace=False)
customers_raw.loc[bad_age_idx, "age"] = rng.choice([-5, 0, 150, 200], size=len(bad_age_idx))
case_idx = rng.choice(customers_raw.index, size=int(0.05 * len(customers_raw)), replace=False)
customers_raw.loc[case_idx, "country"] = customers_raw.loc[case_idx, "country"].str.upper()
gender_typo_idx = rng.choice(customers_raw.dropna(subset=["gender"]).index,
                              size=int(0.02 * len(customers_raw)), replace=False)
customers_raw.loc[gender_typo_idx, "gender"] = customers_raw.loc[gender_typo_idx, "gender"].str.lower()
# duplicate customers (exact dupes of full rows, simulating double signup entry)
dupe_rows = customers_raw.sample(int(0.01 * len(customers_raw)), random_state=1)
customers_raw = pd.concat([customers_raw, dupe_rows], ignore_index=True)

# subscriptions: cancelled without cancellation_date, inconsistent status labels
subs_raw = subscriptions.copy()
bad_status_idx = rng.choice(
    subs_raw[subs_raw["subscription_status"] == "Cancelled"].index,
    size=int(0.015 * len(subs_raw)), replace=False
)
subs_raw.loc[bad_status_idx, "cancellation_date"] = pd.NaT
label_noise_idx = rng.choice(subs_raw.index, size=int(0.01 * len(subs_raw)), replace=False)
subs_raw.loc[label_noise_idx, "subscription_status"] = subs_raw.loc[label_noise_idx, "subscription_status"].str.lower()
subs_raw = inject_missing(subs_raw, ["discount_percentage"], frac=0.01)

# transactions: duplicates, negative amounts where inappropriate, invalid dates, orphan sub ids
txns_raw = transactions.copy()
dupe_txn = txns_raw.sample(int(0.008 * len(txns_raw)), random_state=2)
txns_raw = pd.concat([txns_raw, dupe_txn], ignore_index=True)
bad_amt_idx = rng.choice(
    txns_raw[txns_raw["transaction_type"] == "Subscription Charge"].index,
    size=int(0.004 * len(txns_raw)), replace=False
)
txns_raw.loc[bad_amt_idx, "amount"] = -abs(txns_raw.loc[bad_amt_idx, "amount"])  # invalid negative charge
orphan_idx = rng.choice(txns_raw.index, size=int(0.003 * len(txns_raw)), replace=False)
txns_raw.loc[orphan_idx, "subscription_id"] = txns_raw["subscription_id"].max() + rng.integers(1000, 5000, size=len(orphan_idx))
txns_raw = inject_missing(txns_raw, ["payment_status"], frac=0.01)

# support tickets: missing satisfaction score, inconsistent issue_type casing
tickets_raw = support_tickets.copy()
tickets_raw = inject_missing(tickets_raw, ["satisfaction_score", "resolution_time_hours"], frac=0.03)
case_idx2 = rng.choice(tickets_raw.index, size=int(0.04 * len(tickets_raw)), replace=False)
tickets_raw.loc[case_idx2, "issue_type"] = tickets_raw.loc[case_idx2, "issue_type"].str.lower()

# activity: occasional missing session data
activity_raw = inject_missing(customer_activity.copy(), ["session_minutes", "feature_usage_count"], frac=0.015)

print("Writing raw CSVs to data/raw/ ...")
customers_raw.to_csv(RAW_DIR / "customers.csv", index=False)
PLANS.to_csv(RAW_DIR / "plans.csv", index=False)
subs_raw.to_csv(RAW_DIR / "subscriptions.csv", index=False)
txns_raw.to_csv(RAW_DIR / "transactions.csv", index=False)
activity_raw.to_csv(RAW_DIR / "customer_activity.csv", index=False)
tickets_raw.to_csv(RAW_DIR / "support_tickets.csv", index=False)
marketing_campaigns.to_csv(RAW_DIR / "marketing_campaigns.csv", index=False)
customer_campaign_interactions.to_csv(RAW_DIR / "customer_campaign_interactions.csv", index=False)

print("\n=== RAW DATA GENERATION COMPLETE ===")
for name, df in [
    ("customers", customers_raw), ("plans", PLANS), ("subscriptions", subs_raw),
    ("transactions", txns_raw), ("customer_activity", activity_raw),
    ("support_tickets", tickets_raw), ("marketing_campaigns", marketing_campaigns),
    ("customer_campaign_interactions", customer_campaign_interactions),
]:
    print(f"  {name:35s} {len(df):>10,} rows")
