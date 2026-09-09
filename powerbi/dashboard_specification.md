# Power BI Dashboard Specification

**Project:** Customer Retention Intelligence Platform (NovaStream)
**Report title:** Customer Retention Intelligence
**Pages:** 5
**Data model:** see `data_model.md` | **Measures:** see `dax_measures.md`

This spec is written so the dashboard can be built/imported directly in
Power BI Desktop using the tables in `data/processed/` and `outputs/`.
Numbers cited as examples below are the actual figures produced by this
project's pipeline (see `reports/business_insights.md` for the full list).

---

## Page 1 — Executive Overview

**Purpose:** a 10-second read for a VP of Customer Success or CFO.

**KPI cards (top row):**
| Card | Measure | Example value |
|---|---|---|
| Total Customers | `[Total Customers]` | 52,000 |
| Active Customers | `[Active Customers]` | 41,266 |
| Churn Rate | `[Churn Rate]` | 20.64% |
| Retention Rate | `[Retention Rate]` | 79.36% |
| Monthly Revenue | `[Monthly Revenue]` | ~$430K (latest month) |
| Revenue at Risk | `[Revenue at Risk]` | ~$1.26M |

**Charts (middle):**
- **Customer growth** — line/area chart, `signup_date` (Date hierarchy, Month)
  on X, `[Total Customers]` (cumulative, via a running-total measure) on Y.
- **Churn trend** — line chart, cancellation month on X, count of cancelled
  subscriptions on Y (use `USERELATIONSHIP` to `cancellation_date`).
- **Revenue trend** — column chart, transaction month on X, `[Monthly Revenue]` on Y.
- **Churn by plan** — bar chart, `plans[plan_name]` on Y, `[Churn Rate]` on X.

**Executive insight text box (bottom):** dynamic text using a measure that
concatenates the top finding, e.g. *"Monthly-billing customers churn at
23.5% vs. 14.6% for annual customers — the single largest churn-rate gap in
the dataset."* (See `reports/business_insights.md` Finding #1.)

**Filters (page-level slicers):** Date range, Region.

---

## Page 2 — Customer Segmentation

**Purpose:** understand who the customers are and how RFM segments differ.

**Visuals:**
- **RFM segment donut/treemap** — `customer_segments[segment]`, size = customer count.
- **Customers by region** — bar chart.
- **Customers by acquisition channel** — bar chart.
- **Tenure distribution** — histogram (bucketed `tenure_months`).
- **Segment churn rate** — bar chart, `customer_segments[segment]` on Y, churn rate on X.
- **Segment revenue** — bar chart, `customer_segments[segment]` on Y, `[Total Revenue]` on X
  (from `customer_segments[monetary]` summed, or joined to `transactions`).

**Filters:** Date, Region, Plan, Acquisition Channel, Segment (all as slicers
in a filter pane on the left).

**Design note:** color-code segments consistently across every page (e.g.
VIP = gold, At Risk = orange, Lost = gray) using a shared color-by-value rule.

---

## Page 3 — Churn & Retention

**Purpose:** diagnose where and why churn is happening.

**Visuals:**
- **Monthly churn (count + rate)** — combo chart, cancellation month on X,
  bars = cancellation count, line = churn rate %.
- **Retention trend** — line chart, `[Retention Rate]` by month.
- **Churn by plan** — bar chart.
- **Churn by billing cycle** — bar chart (Monthly vs Annual).
- **Churn by tenure bucket** — bar chart (0-3mo, 3-6mo, 6-12mo, 12mo+).
- **Churn by engagement tercile** — bar chart (Low/Medium/High engagement).
- **Cohort retention heatmap** — matrix visual, rows = cohort month, columns
  = M0/M1/M2/M3/M6/M12, values = retention %, conditional formatting
  (red→green color scale). Source: `outputs/tables/cohort_retention.csv`.

---

## Page 4 — Revenue Intelligence

**Purpose:** connect churn to dollars, and show where money is concentrated.

**Visuals:**
- **MRR trend** — line chart.
- **Revenue growth %** — column chart with a 0-line reference.
- **Revenue by plan** — bar/treemap.
- **Revenue by region** — map (if geocoding available) or bar chart.
- **Revenue by acquisition channel** — bar chart.
- **Revenue lost to churn** — KPI card + trend.
- **Revenue at risk** — KPI card + breakdown by plan/region (stacked bar).

**Highlighted callout:** "High-Value Customers at Risk" card — count and
revenue of customers in `retention_priority = "Priority 1"`, styled as a
prominent alert-colored card (e.g. red background) at the top-right of the page.

---

## Page 5 — Retention Action Center

**Purpose:** an operational worklist a Customer Success/Retention team could
actually use day-to-day.

**Visuals:**
- **Risk distribution** — 3 KPI cards: High / Medium / Low risk customer counts.
- **Revenue at risk** — KPI card.
- **High-value customers at risk** — KPI card (Priority 1 count).
- **Retention worklist table** — the centerpiece of the page. Columns:

  | Customer | Plan | Revenue | Churn Probability | Risk Level | Retention Priority |
  |---|---|---|---|---|---|
  | (customer_id) | plan_name | annualized_revenue | churn_probability | risk_level | retention_priority |

  Source: `outputs/tables/retention_priority.csv` joined to
  `outputs/model_results/customer_churn_risk.csv`. Sort descending by
  `churn_probability`. Conditionally format `Risk Level` (red/amber/green)
  and `Churn Probability` (data bars).

**Filter:** a slicer/button group for **"High Risk + High Value"** that sets
`retention_priority = "Priority 1 - High Risk / High Value"` — implement as
a bookmark-driven filter button so a retention manager can click one button
to see exactly who to call first.

**Design note:** this page should look like a CRM worklist, not an analytics
chart — dense table, minimal decorative chart-junk, fast to scan.

---

## Cross-page design guidelines

- **Theme:** consistent brand palette (e.g. deep blue `#1B4965` primary,
  teal `#2E86AB` secondary, red/orange `#A23B72`/`#F2A541` for risk).
- **Typography:** Segoe UI (Power BI default) throughout; KPI card numbers
  large (28–36pt), labels small caps.
- **Tooltips:** enable report-page tooltips showing customer-level detail
  (segment, tenure, last activity) on hover over any chart.
- **Navigation:** add a left-hand nav bar (bookmark buttons) so users can
  jump between the 5 pages without using page tabs.
- **Mobile layout:** create a simplified mobile layout for Page 1 (KPI
  cards) and Page 5 (worklist) at minimum, since this dashboard is likely to
  be checked on a phone by a CS manager between meetings.
