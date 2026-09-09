# Executive Summary

**Project:** Customer Retention Intelligence Platform
**Company:** NovaStream (subscription/SaaS)
**Prepared for:** Executive leadership / Customer Success leadership

---

## The Problem

NovaStream has seen rising customer churn and had no systematic way to
answer four questions: **who is churning, why, how much revenue is at risk,
and who should we call first?** This project analyzed 52,000 customers,
52,563 subscriptions, and 393,498 billing transactions across 24 months to
answer them.

## Headline Numbers

| Metric | Value |
|---|---:|
| Total customers | 52,000 |
| Active customers | 41,266 |
| Overall churn rate | 20.64% |
| Total revenue collected | $9,908,446.17 |
| Annualized recurring revenue lost to churn (already happened) | $1,775,700.24 |
| Revenue at Risk (ML-forecasted, Active customers) | $1,255,230.23 |
| Customers flagged High risk by the churn model | 8,884 |

## What's Driving Churn

1. **Billing cycle is the single largest lever.** Monthly-billed customers
   churn at 23.5% vs. 14.6% for annual customers — a gap large enough to be
   worth an annual-plan incentive program.
2. **Entry-level plans churn more.** Basic-tier churn (24.3%) is nearly
   double Enterprise-tier churn (14.8%), and Basic is NovaStream's largest
   plan by customer count — so it's also the largest *source* of churn
   events in absolute terms.
3. **The first 90 days are the highest-risk period.** Churned customers
   stay an average of ~5.8 months before leaving; a large share leave in
   the first 3 months.
4. **Declining engagement, unresolved support tickets, and low
   satisfaction all show up before a customer cancels** — three
   independent, statistically significant early-warning signals that a
   proactive program could act on.

## Highest-Risk / Highest-Value Segments

- The top 10% of customers by revenue generate **33% of all revenue**
  ($3.27M) — losing even a few of them matters disproportionately.
- **5,407 high-value Active customers** currently show low satisfaction or
  an unresolved support ticket, representing **$2.38M** in historical
  revenue exposure.
- RFM segmentation shows **VIP + Dormant customers hold over half of all
  revenue** — the Dormant segment in particular (low recent activity, still
  technically active) is a prime target for proactive re-engagement before
  they lapse into Lost.

## What We Built

A Random Forest churn prediction model (ROC-AUC 0.94, catching 82.5% of
customers who actually churn) scores every customer's churn probability and
feeds a **Retention Priority worklist** — ranking Active customers into 4
tiers by combining churn risk with customer value, so a retention team
knows exactly who to call first. This is paired with a 5-page Power BI
dashboard specification (Executive Overview, Customer Segmentation, Churn &
Retention, Revenue Intelligence, and a Retention Action Center built to
function like a CRM worklist).

## Recommended Actions

1. Launch an annual-plan incentive test targeted at monthly customers past
   their first 60–90 days.
2. Build a first-90-day onboarding push (product tours, milestone emails,
   proactive check-ins) — the period with the highest churn risk.
3. Stand up an automated alert when a customer's engagement drops or a
   support ticket goes unresolved, routed to a retention specialist.
4. Create a dedicated "VIP care" track for top-decile-revenue customers.
5. Operationalize the churn model's weekly output as a retention team
   worklist, starting with the 198 "Priority 1: High Risk / High Value"
   customers.
6. Run the proposed A/B test (see `reports/business_insights.md`) before
   rolling out any retention offer broadly, to confirm it actually moves
   churn and produces a positive ROI.

## Caveats

This analysis uses a statistically realistic *synthetic* dataset built for
this portfolio project, not NovaStream's real production data — absolute
dollar figures should be read as illustrative of the *method*, not as real
company financials. All modeling avoided data leakage (no post-cancellation
information was used to predict churn), and statistical findings are
reported as associations, not proven causes — see `reports/methodology.md`
for full detail.
