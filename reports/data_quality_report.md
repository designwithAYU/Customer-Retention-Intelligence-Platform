# Data Quality Report

**Project:** Customer Retention Intelligence Platform (NovaStream)

This report documents every data quality issue discovered in the raw NovaStream datasets during the cleaning stage (`src/clean_data.py`), the number and percentage of records affected, the treatment applied, and the reasoning behind that treatment.

| Issue | Records Affected | % Affected | Treatment | Reason |
|---|---:|---:|---|---|
| Duplicate customers (duplicate customer_id) | 520 | 0.99% | Deduplicated (kept first occurrence) | Simulated double-entry during signup; customer_id is the natural key |
| Inconsistent country capitalization | 2,557 | 4.917% | Standardized to title case | Source systems submitted country names in mixed case |
| Inconsistent gender capitalization | 1,040 | 2.0% | Standardized to title case | Manual data entry inconsistency |
| Invalid age (<13 or >100) | 260 | 0.5% | Converted to missing, then imputed | Ages outside plausible human range are data entry errors |
| Missing age (incl. converted invalid ages) | 1,338 | 2.573% | Median imputation by region | Age is needed for demographic segmentation; region median is a reasonable proxy |
| Missing gender | 1,056 | 2.031% | Filled with 'Unknown' category | Preserves the record without fabricating a gender |
| Missing country/region | 1,070 | 2.058% | Filled with 'Unknown' category | Small share of records; dropping would lose otherwise valid revenue history |
| Missing referral_source | 1,103 | 2.121% | Filled with 'Not Captured' | Referral source is optional metadata, not critical to core analysis |
| Inconsistent subscription_status labels (lowercase) | 525 | 0.999% | Standardized to title case ('Active'/'Cancelled') | Multiple source systems used different casing conventions |
| Cancelled subscriptions missing cancellation_date | 788 | 1.499% | Back-filled from end_date, or set to observation cutoff if both missing | Cancellation date is required for churn timing and cohort analysis |
| Missing discount_percentage | 524 | 0.997% | Filled with 0 (no discount) | Absence of a discount record most plausibly means no discount was applied |
| Invalid dates (end_date before start_date) | 0 | 0.0% | Cleared end/cancellation date and reset status to Active | A cancellation date earlier than signup is logically impossible |
| Duplicate transactions | 3,112 | 0.782% | Removed duplicate rows | Duplicate billing events caused by webhook/retry logic, not genuine repeat charges |
| Transactions with orphan subscription_id | 1,193 | 0.3% | Excluded | Cannot be reliably attributed to a valid subscription; likely test/corrupted records |
| Invalid negative Subscription Charge amounts | 1,629 | 0.414% | Converted to absolute value | Negative charges (not refunds) indicate a sign error at the source system |
| Missing payment_status | 3,951 | 1.004% | Filled with 'Unknown' | Preserves the transaction record for revenue totals while flagging incomplete status data |
| Transactions with orphan customer_id | 0 | 0.0% | Excluded | No matching customer record; cannot be attributed to a real customer |
| Missing session_minutes | 14,703 | 1.505% | Median imputation | Small share of tracking-pixel failures; median avoids distorting engagement trend |
| Missing feature_usage_count | 14,526 | 1.487% | Filled with 0 | Absence of a logged event most plausibly means no feature usage was recorded that period |
| Activity records with orphan customer_id | 0 | 0.0% | Excluded | No matching customer record |
| Inconsistent issue_type capitalization | 3,129 | 4.0% | Standardized to title case | Ticketing system categories entered inconsistently by different support agents |
| Missing satisfaction_score | 2,240 | 2.863% | Median imputation | Customers do not always complete post-ticket satisfaction surveys |
| Missing resolution_time_hours | 2,376 | 3.037% | Median imputation | Open/in-progress tickets at time of export lack a final resolution time |

## Summary
- Total data quality checks performed: **23**
- Total records affected across all checks: **57,640** (note: a single record can be affected by more than one issue, so this is not a unique-record count).

## Assumptions & Limitations
- Median imputation was used for numeric fields to limit the influence of outliers.
- Categorical fields with missing values were filled with an explicit `Unknown` / `Not Captured` label rather than the mode, to avoid silently fabricating customer attributes.
- Records that could not be attributed to a valid customer or subscription (orphan foreign keys) were excluded from the processed datasets, since they cannot be reliably analyzed.
- All cleaning logic is deterministic and reproducible by re-running `src/clean_data.py` against `data/raw/`.