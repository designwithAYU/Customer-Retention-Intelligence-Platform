# DAX Measures

**Project:** Customer Retention Intelligence Platform (NovaStream)

All measures below assume the relationships described in `data_model.md`.
Where a measure needs to bypass the model's active relationship (e.g. to use
`cancellation_date` instead of `start_date`), `USERELATIONSHIP()` is used
explicitly.

---

## Customer KPIs

```DAX
Total Customers =
DISTINCTCOUNT ( customers[customer_id] )
```

```DAX
Active Customers =
CALCULATE (
    DISTINCTCOUNT ( subscriptions[customer_id] ),
    subscriptions[subscription_status] = "Active"
)
```
*Note: uses the customer's most recent subscription; if importing raw
`subscriptions`, prefer filtering on the pre-computed `customer_churn_risk`
or `customer_360` table, which already resolves to one row per customer.*

```DAX
Churned Customers =
[Total Customers] - [Active Customers]
```

```DAX
New Customers =
CALCULATE (
    DISTINCTCOUNT ( customers[customer_id] ),
    USERELATIONSHIP ( 'Date'[date], customers[signup_date] )
)
```

```DAX
Churn Rate =
DIVIDE ( [Churned Customers], [Total Customers], 0 )
```

```DAX
Retention Rate =
1 - [Churn Rate]
```

```DAX
Customer Growth % =
VAR CurrentCustomers = [Total Customers]
VAR PriorCustomers =
    CALCULATE ( [Total Customers], DATEADD ( 'Date'[date], -1, MONTH ) )
RETURN
    DIVIDE ( CurrentCustomers - PriorCustomers, PriorCustomers, 0 )
```

```DAX
Average Tenure (Days) =
AVERAGEX (
    subscriptions,
    DATEDIFF (
        subscriptions[start_date],
        COALESCE ( subscriptions[cancellation_date], TODAY () ),
        DAY
    )
)
```

---

## Revenue KPIs

```DAX
Total Revenue =
CALCULATE (
    SUM ( transactions[amount] ),
    transactions[transaction_type] = "Subscription Charge",
    transactions[payment_status] = "Success"
)
```

```DAX
Monthly Revenue =
CALCULATE ( [Total Revenue], USERELATIONSHIP ( 'Date'[date], transactions[transaction_date] ) )
```

```DAX
MRR (Monthly Recurring Revenue) =
CALCULATE (
    SUMX (
        FILTER ( subscriptions, subscriptions[subscription_status] = "Active" ),
        IF (
            subscriptions[billing_cycle] = "Annual",
            subscriptions[monthly_price] / 12,
            subscriptions[monthly_price]
        )
    )
)
```

```DAX
Revenue Growth % =
VAR CurrentRev = [Monthly Revenue]
VAR PriorRev = CALCULATE ( [Monthly Revenue], DATEADD ( 'Date'[date], -1, MONTH ) )
RETURN
    DIVIDE ( CurrentRev - PriorRev, PriorRev, 0 )
```

```DAX
ARPU =
DIVIDE ( [Total Revenue], [Total Customers], 0 )
```

```DAX
Revenue Lost to Churn (Annualized) =
CALCULATE (
    SUMX (
        FILTER ( subscriptions, subscriptions[subscription_status] = "Cancelled" ),
        IF (
            subscriptions[billing_cycle] = "Monthly",
            subscriptions[monthly_price] * 12,
            subscriptions[monthly_price]
        )
    )
)
```

```DAX
Revenue at Risk =
SUMX (
    customer_churn_risk,
    RELATED ( retention_priority[annualized_revenue] ) * customer_churn_risk[churn_probability]
)
```
*Simpler alternative if `retention_priority` isn't loaded: sum
`outputs/tables/retention_priority.csv`'s pre-computed `revenue_at_risk`
column directly with `SUM ( retention_priority[revenue_at_risk] )`.*

```DAX
Customer Lifetime Value (CLV) =
AVERAGEX (
    VALUES ( customers[customer_id] ),
    CALCULATE (
        SUM ( transactions[amount] ),
        transactions[transaction_type] = "Subscription Charge",
        transactions[payment_status] = "Success"
    )
)
```

---

## Engagement KPIs

```DAX
Average Sessions =
AVERAGE ( customer_activity[sessions] )
```

```DAX
Average Session Duration =
AVERAGE ( customer_activity[session_minutes] )
```

```DAX
Feature Usage (Avg) =
AVERAGE ( customer_activity[feature_usage_count] )
```

```DAX
Support Tickets =
COUNTROWS ( support_tickets )
```

```DAX
Average Satisfaction =
AVERAGE ( support_tickets[satisfaction_score] )
```

---

## Churn & Risk KPIs

```DAX
High Risk Customers =
CALCULATE (
    DISTINCTCOUNT ( customer_churn_risk[customer_id] ),
    customer_churn_risk[risk_level] = "High"
)
```

```DAX
High Value Customers at Risk =
CALCULATE (
    DISTINCTCOUNT ( retention_priority[customer_id] ),
    retention_priority[retention_priority] = "Priority 1 - High Risk / High Value"
)
```

```DAX
Avg Churn Probability =
AVERAGE ( customer_churn_risk[churn_probability] )
```

---

## Risk threshold parameters (What-If parameter, optional)

To let a Customer Success manager tune thresholds live in the report, add a
Power BI **What-If Parameter** named `High Risk Threshold` (0.5–0.9, step
0.05, default 0.70) and `Medium Risk Threshold` (0.2–0.6, step 0.05, default
0.40), then re-derive `Risk Level (Dynamic)`:

```DAX
Risk Level (Dynamic) =
VAR HighT = [High Risk Threshold Value]
VAR MedT = [Medium Risk Threshold Value]
VAR P = SELECTEDVALUE ( customer_churn_risk[churn_probability] )
RETURN
    SWITCH (
        TRUE (),
        P >= HighT, "High",
        P >= MedT, "Medium",
        "Low"
    )
```
This mirrors the configurable `RISK_THRESHOLDS` dictionary in
`src/churn_model.py`, so the SQL, Python, and BI layers stay consistent.
