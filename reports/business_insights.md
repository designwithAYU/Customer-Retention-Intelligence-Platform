# Business Insights

**Project:** Customer Retention Intelligence Platform (NovaStream)

All figures below are calculated directly from this project's generated
dataset (52,000 customers, 52,563 subscriptions, 393,498 transactions) using
the SQL queries in `sql/` and the Python analysis in `src/`. None are
invented.

---

### Finding 1 — Monthly-billing customers churn at a much higher rate than annual customers

**Evidence:** Monthly billing churn = **23.49%** vs. Annual billing churn =
**14.61%** (a ~9-point gap). A chi-square test of independence between
billing cycle and churn is highly significant (χ² = 543.5, p < 0.001).

**Business Impact:** Monthly billing carries a materially higher risk of
losing the customer relationship every 30 days. With 35,773 monthly
subscriptions on file, even a modest shift of monthly customers to annual
plans would meaningfully reduce total churned customers.

**Recommendation:** Test annual-plan incentives (e.g. one free month, or a
modest discount) targeted at monthly customers past their first 60–90 days,
when switching cost/friction is lower.

---

### Finding 2 — Entry-level plans churn substantially more than premium/enterprise plans

**Evidence:** Churn by plan — Basic **24.26%**, Standard **20.59%**, Premium
**18.37%**, Enterprise **14.82%**. A chi-square test confirms plan and churn
are significantly associated (χ² = 318.6, p < 0.001).

**Business Impact:** Basic-plan customers are ~1.6x as likely to churn as
Enterprise customers, yet Basic is the largest plan by customer count
(18,114 customers). This is where the largest *volume* of churn events
originates, even though per-customer revenue is lower.

**Recommendation:** Investigate onboarding and feature-adoption gaps
specific to Basic-tier customers; consider a guided upgrade path once usage
patterns suggest a customer would benefit from Standard/Premium features.

---

### Finding 3 — Declining engagement and support friction both precede churn

**Evidence:** Churned customers average **6.39** sessions per period vs.
**7.05** for retained customers (t = -19.5, p < 0.001); churned customers
average **1.83** support tickets vs. **1.42** for retained customers (t =
25.9, p < 0.001); and churned customers report lower average satisfaction
(**2.63** vs. **2.94**, t = -28.6, p < 0.001).

**Business Impact:** These are three independent, statistically significant
early-warning signals available *before* a customer cancels — exactly the
signals a proactive retention program needs.

**Recommendation:** Build an automated alert when a customer's engagement
drops and/or an unresolved ticket persists, and route them to a retention
specialist before they reach the cancellation page. (See Finding 8 below for
the ML-based version of this signal.)

**Caveat:** These are statistical associations in observational data, not
proven causal effects — see `reports/methodology.md`, Section 9.

---

### Finding 4 — Churn is heavily front-loaded in the first 3 months of tenure

**Evidence:** Churn rate by tenure bucket: 0–3 months = **34.3%**, 3–6
months = **27.2%**, 6–12 months (partial data) noticeably lower, 12+ months
lowest. Average tenure of churned customers = **174.98 days** (~5.8 months)
vs. average tenure of retained (still-active) customers = **298.46 days**
(~9.8 months, and still growing since they haven't churned).

**Business Impact:** Onboarding is the single highest-risk period in the
customer lifecycle.

**Recommendation:** Invest disproportionately in first-90-day onboarding
(product tours, milestone emails, early check-in calls for higher-value
plans) rather than spreading retention budget evenly across tenure.

---

### Finding 5 — Revenue is highly concentrated in a small share of customers

**Evidence:** The top revenue decile (5,102 customers, ~10% of the base)
contributes **$3,274,925.80**, or **33.05%** of all revenue collected.

**Business Impact:** A small group of high-value customers disproportionately
drives NovaStream's revenue; losing even a handful of them has an outsized
financial effect compared to losing an average customer.

**Recommendation:** Assign a named retention owner or "VIP care" track for
top-decile customers, distinct from the general retention workflow.

---

### Finding 6 — A meaningful pool of high-value customers is currently at risk

**Evidence:** 5,407 customers in the top revenue quartile are Active but
show low satisfaction (≤3) or at least one unresolved support ticket,
representing **$2,378,567.44** in historical revenue exposure (SQL Q41,
`sql/07_advanced_analysis.sql`). The machine-learning model separately
estimates total **Revenue at Risk = $1,255,230.23** (probability-weighted,
across all Active customers — see Finding 8).

**Business Impact:** These two independent methods (a simple SQL heuristic
and a full ML model) both point to a concrete, actionable dollar figure that
justifies investment in a retention program.

**Recommendation:** Prioritize the "Priority 1" retention list (see
`outputs/tables/retention_priority.csv`) for immediate outreach.

---

### Finding 7 — RFM segmentation reveals where revenue and risk are concentrated

**Evidence:** Segment breakdown (`outputs/tables/segment_summary.csv`):

| Segment | Customers | % of customers | Revenue | % of revenue | Churn rate |
|---|---:|---:|---:|---:|---:|
| Dormant | 10,816 | 20.80% | $2,579,278 | 26.03% | 0.00%* |
| VIP | 7,083 | 13.62% | $2,561,913 | 25.86% | 1.13% |
| Loyal | 8,832 | 16.98% | $1,948,651 | 19.67% | 5.36% |
| Lost | 9,277 | 17.84% | $1,142,701 | 11.53% | 100.00% |
| Potential Loyal | 11,848 | 22.78% | $1,079,962 | 10.90% | 6.44% |
| New | 3,437 | 6.61% | $315,670 | 3.19% | 4.10% |
| At Risk | 707 | 1.36% | $280,272 | 2.83% | 0.00%* |

*\*"Dormant" and "At Risk" customers show 0% churn in this snapshot because
they remain on `Active` subscription status (often annual-cycle customers
who simply haven't transacted recently) — their low recency score signals
early warning, not a completed cancellation. This is an important nuance
for interpreting RFM recency correctly (see `reports/methodology.md`).*

**Business Impact:** VIP and Dormant customers together hold >50% of all
revenue. Dormant customers, despite currently showing no churn, warrant
proactive re-engagement precisely because low recency is historically a
leading indicator.

**Recommendation:** Launch a distinct re-engagement campaign for the
Dormant segment before they convert to Lost.

---

### Finding 8 — The Random Forest churn model substantially outperforms Logistic Regression and identifies engagement/recency as the top predictive drivers

**Evidence:** Model comparison on a held-out 25% test set:

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---:|---:|---:|---:|---:|
| Logistic Regression | 65.01% | 33.77% | 72.34% | 46.04% | 0.7407 |
| **Random Forest** | **89.42%** | **70.95%** | **82.48%** | **76.28%** | **0.9447** |

Top predictive features (Random Forest importances):
`recency_days` (50.8%), `tenure_days` (18.4%), `total_transactions` (7.5%),
`total_revenue` (4.8%), `engagement_trend_ratio` (2.6%).

**Business Impact:** The model catches **82.5% of customers who actually
churn** (recall) at a precision of 71% — a strong basis for a proactive
retention worklist without overwhelming the retention team with false
alarms. It flags **8,884 customers as High risk** and **7,585 as Medium
risk** out of 52,000.

**Recommendation:** Operationalize the model's churn probability score as a
weekly-refreshed retention worklist (see Power BI Page 5, "Retention Action
Center"), prioritized using the `retention_priority` tiers.

---

### Finding 9 — Discounts show a modest, not dramatic, relationship with churn

**Evidence:** See `outputs/figures/15_churn_by_discount.png`. Discounted
customers do not show a uniformly lower churn rate than full-price
customers across all discount tiers — the effect is present but noisy,
consistent with the project's design goal of avoiding an artificially clean
"discounts always help" pattern.

**Business Impact:** Broad discounting is not, by itself, a reliable
retention lever in this data.

**Recommendation:** If discounting is used for retention, target it
narrowly (e.g. only for customers already flagged High risk by the churn
model) rather than as a blanket acquisition/retention tool.

---

### Finding 10 — Retention has been roughly stable across cohorts, with no clear structural decline

**Evidence:** Comparing early vs. later signup cohorts' M3 retention:
**90.9%** (early cohorts) vs. **91.0%** (later cohorts) — essentially flat
(`src/cohort_analysis.py` output; see `outputs/figures/18_cohort_retention_heatmap.png`).

**Business Impact:** The rising churn concern that motivated this project
(per the brief) is not explained by a systemic, worsening cohort trend in
this dataset — it is better explained by the plan-mix, billing-cycle, and
engagement/support drivers identified in Findings 1–4 above.

**Recommendation:** Focus retention investment on the *segment-level*
drivers identified above (plan tier, billing cycle, onboarding period,
engagement/support signals) rather than assuming a company-wide, worsening
trend requiring a blanket fix.

---

## Retention Recommendations (summary)

1. **Onboarding improvements** — front-load retention effort into the
   first 90 days (Finding 4).
2. **Targeted retention offers** — narrow, risk-flagged discounting rather
   than broad promotions (Finding 9).
3. **Engagement campaigns** — automated nudges when session/feature usage
   drops (Finding 3).
4. **Support improvements** — faster resolution and satisfaction recovery
   for at-risk customers (Finding 3).
5. **Plan restructuring** — investigate Basic-tier feature gaps (Finding 2).
6. **Annual-plan incentives** — shift monthly customers to annual billing
   post-onboarding (Finding 1).
7. **High-value customer interventions** — a dedicated VIP retention track
   (Findings 5–6).
8. **Proactive outreach** — operationalize the ML risk score into a weekly
   worklist (Finding 8).

## A/B Test Proposal (hypothetical — not yet run)

**Objective:** Test whether a personalized retention intervention reduces
churn among High-risk customers (per the ML model).

- **Control:** No retention offer/outreach (business as usual).
- **Treatment:** Personalized retention intervention (e.g. a proactive
  check-in call + a modest, risk-targeted discount) for customers flagged
  High risk.
- **Randomization unit:** Customer, stratified by plan and risk tier.
- **Primary metric:** 90-day churn rate (Treatment vs. Control).
- **Secondary metrics:** Retention rate, revenue retained, discount
  redemption/conversion rate, intervention cost per customer, and ROI
  (revenue retained − intervention cost).
- **Sample size:** Should be calculated from the observed effect sizes
  above (e.g. the ~9-point billing-cycle churn gap) using a standard
  two-proportion power calculation before launch.

**This is a proposed experiment design only** — no actual A/B test has been
run as part of this project, and no improvement percentage is claimed until
one is.
