# Power BI Data Model

**Project:** Customer Retention Intelligence Platform (NovaStream)

This document describes how to load the NovaStream tables into Power BI
Desktop and how to relate them. It assumes you are importing from
PostgreSQL (`sql/01_schema.sql`) or, equivalently, from the cleaned CSVs in
`data/processed/` if a database server is not available.

## 1. Getting data into Power BI

**Option A — from PostgreSQL**
`Get Data → PostgreSQL database` → point at the NovaStream database → select
all 8 base tables plus the `customer_360` view → Import mode (recommended
for a dataset this size; DirectQuery works too but Import gives faster
visuals).

**Option B — from CSV (no database available)**
`Get Data → Text/CSV` → import each file in `data/processed/` individually:
`customers.csv`, `plans.csv`, `subscriptions.csv`, `transactions.csv`,
`customer_activity.csv`, `support_tickets.csv`, `marketing_campaigns.csv`,
`customer_campaign_interactions.csv`.

**Option C — from the pre-computed analytical tables**
For a faster build, also import the derived tables produced by the Python
pipeline, which avoid re-deriving RFM/churn-risk logic inside DAX:
- `outputs/tables/customer_segments.csv` (RFM segments)
- `outputs/model_results/customer_churn_risk.csv` (churn probability + risk tier)
- `outputs/tables/retention_priority.csv` (retention priority score)
- `outputs/tables/cohort_retention.csv` (cohort retention matrix)

## 2. Recommended table roles

| Table | Role | Grain |
|---|---|---|
| `customers` | Dimension | 1 row per customer |
| `plans` | Dimension | 1 row per plan |
| `subscriptions` | Fact (slowly changing) | 1 row per subscription lifecycle |
| `transactions` | Fact | 1 row per billing event |
| `customer_activity` | Fact | 1 row per customer per ~2-week period |
| `support_tickets` | Fact | 1 row per support ticket |
| `marketing_campaigns` | Dimension | 1 row per campaign |
| `customer_campaign_interactions` | Fact | 1 row per interaction |
| `customer_churn_risk` | Derived fact | 1 row per customer (latest score) |
| `customer_segments` | Derived dimension/fact | 1 row per customer (RFM) |
| `retention_priority` | Derived fact | 1 row per active customer |
| `date` | Dimension (create in Power BI) | 1 row per day |

## 3. Relationships

Build these relationships in Model view (all single-direction, "one" side
first):

- `customers[customer_id]` **1 → ∗** `subscriptions[customer_id]`
- `plans[plan_id]` **1 → ∗** `subscriptions[plan_id]`
- `customers[customer_id]` **1 → ∗** `transactions[customer_id]`
- `subscriptions[subscription_id]` **1 → ∗** `transactions[subscription_id]`
- `customers[customer_id]` **1 → ∗** `customer_activity[customer_id]`
- `customers[customer_id]` **1 → ∗** `support_tickets[customer_id]`
- `marketing_campaigns[campaign_id]` **1 → ∗** `customer_campaign_interactions[campaign_id]`
- `customers[customer_id]` **1 → ∗** `customer_campaign_interactions[customer_id]`
- `customers[customer_id]` **1 → 1** `customer_churn_risk[customer_id]`
- `customers[customer_id]` **1 → 1** `customer_segments[customer_id]`
- `customers[customer_id]` **1 → 1** `retention_priority[customer_id]` (left join — only Active customers have a row)
- `date[date]` **1 → ∗** to the date column on `transactions`, `customer_activity`,
  `support_tickets`, `subscriptions[start_date]`/`[cancellation_date]` (use
  **inactive** relationships + `USERELATIONSHIP()` in DAX for the extra
  subscription date roles, since a table can only have one active
  relationship per dimension by default).

## 4. Date table

Create a calculated date table spanning the full data range:

```DAX
Date =
CALENDAR (DATE(2023,9,1), DATE(2025,9,1))
```
Then add `Year`, `Month`, `Month Name`, `Year-Month` columns, and mark it as
a **Date Table** (Modeling → Mark as Date Table).

## 5. Star-schema diagram (conceptual)

```
                       ┌─────────────┐
                       │    plans    │
                       └──────┬──────┘
                              │
┌─────────────┐        ┌─────▼──────────┐        ┌───────────────┐
│  customers  │◄───────┤ subscriptions  │        │ marketing_     │
│ (dimension) │        │    (fact)      │        │ campaigns      │
└──────┬──────┘        └────────────────┘        └───────┬────────┘
       │                                                   │
       ├──────────► transactions (fact)                    │
       ├──────────► customer_activity (fact)                │
       ├──────────► support_tickets (fact)                   │
       └──────────► customer_campaign_interactions (fact) ◄──┘
       │
       ├──────────► customer_churn_risk (1:1 derived fact)
       ├──────────► customer_segments (1:1 derived dimension)
       └──────────► retention_priority (1:1 derived fact, Active only)
```

## 6. Naming & folder conventions

Organize measures into Display Folders in Power BI:
- `Customer KPIs`
- `Revenue KPIs`
- `Engagement KPIs`
- `Churn & Risk KPIs`

See `powerbi/dax_measures.md` for every measure definition.
