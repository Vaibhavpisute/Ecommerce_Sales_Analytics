# DAX measures

All measures are stored in the semantic model (`powerbi/EcommerceSales.SemanticModel`). This file is written by `powerbi/build_project.py` from the same definitions, so it always matches the model.

Revenue means the item price without freight, for valid sales only (not canceled or unavailable).

## The 7 required measures

| Measure | What it does | Expected value (from the SQL results, to compare in Power BI) |
|---|---|---|
| **Total Revenue** | Sum of item prices (without freight) of valid sales. | 13,494,400.74 with no filters (Q2 sum of all months; Q15 'All orders'). |
| **Total Orders** | Number of valid orders that have items. | 98,199 with no filters (Q2 sum of all months). |
| **AOV** | Average order value = revenue / orders. | 137.42 with no filters (Q15 'All orders'). |
| **MoM Growth %** | Month-over-month revenue growth. Empty unless a single month is in scope and both months are full months (same rule as SQL Q3). | SQL Q3 mom_growth_pct for each month from 2017-02 to 2018-08 (for example 2018-08: -3.32%; the KPI card shows -3.3%). |
| **Repeat Customer %** | Share of customers with 2 or more valid orders in the whole data (SQL Q10 repeat_purchase_rate_pct when nothing is filtered). | 3.04% with no filters (SQL Q10: 2,887 of 94,983 customers). |
| **Revenue YTD** | Revenue from 1 January of the year to the date. | At 2018-08-31 it equals the sum of Q2 revenue from 2018-01 to 2018-08. |
| **Average Review Score** | Average review score (1 to 5). | About 4.12 with no filters (4.1164 in the export control numbers). |

## All measures

### Table `fact_order_items`

**Total Revenue** (Sales, format `#,0.00`): Sum of item prices (without freight) of valid sales.

```dax
Total Revenue =
SUM(fact_order_items[price])
```

**Total Orders** (Sales, format `#,0`): Number of valid orders that have items.

```dax
Total Orders =
DISTINCTCOUNT(fact_order_items[order_key])
```

**AOV** (Sales, format `#,0.00`): Average order value = revenue / orders.

```dax
AOV =
DIVIDE([Total Revenue], [Total Orders])
```

**Freight Value** (Sales, format `#,0.00`): Sum of freight.

```dax
Freight Value =
SUM(fact_order_items[freight_value])
```

**Units Sold** (Sales, format `#,0`): Number of items sold.

```dax
Units Sold =
COUNTROWS(fact_order_items)
```

**Revenue Previous Month** (Growth, format `#,0.00`): Revenue of the month before.

```dax
Revenue Previous Month =
CALCULATE([Total Revenue], DATEADD(dim_date[date], -1, MONTH))
```

**MoM Growth %** (Growth, format `0.0%`): Month-over-month revenue growth. Empty unless a single month is in scope and both months are full months (same rule as SQL Q3).

```dax
MoM Growth % =
VAR prevRevenue = [Revenue Previous Month]
VAR bothMonthsComplete =
    MAX(dim_date[analysis_flag]) = 1
        && CALCULATE(MAX(dim_date[analysis_flag]), DATEADD(dim_date[date], -1, MONTH)) = 1
RETURN
    IF(
        HASONEVALUE(dim_date[year_month]) && bothMonthsComplete,
        DIVIDE([Total Revenue] - prevRevenue, prevRevenue)
    )
```

**MoM Growth % (last full month)** (Growth, format `0.0%`): MoM growth of the last full month in the selected dates (for the KPI card).

```dax
MoM Growth % (last full month) =
VAR lastMonth =
    MAXX(
        FILTER(
            VALUES(dim_date[month_start]),
            [Total Revenue] > 0 && CALCULATE(MAX(dim_date[analysis_flag])) = 1
        ),
        dim_date[month_start]
    )
RETURN
    CALCULATE([MoM Growth %], dim_date[month_start] = lastMonth)
```

**Revenue YTD** (Growth, format `#,0`): Revenue from 1 January of the year to the date.

```dax
Revenue YTD =
TOTALYTD([Total Revenue], dim_date[date])
```

**Revenue Share %** (Products, format `0.0%`): Share of the selected categories' revenue.

```dax
Revenue Share % =
DIVIDE([Total Revenue], CALCULATE([Total Revenue], ALLSELECTED(dim_product[category])))
```

**Category Rank** (Products, format `0`): Rank of the category by revenue.

```dax
Category Rank =
RANKX(ALLSELECTED(dim_product[category]), [Total Revenue], , DESC, Dense)
```

**Revenue (Top 10 Categories)** (Products, format `#,0`): Revenue, only for the 10 best categories (other categories are empty and hidden in charts).

```dax
Revenue (Top 10 Categories) =
IF([Category Rank] <= 10, [Total Revenue])
```

**State Rank** (Geography, format `0`): Rank of the customer state by revenue.

```dax
State Rank =
RANKX(ALLSELECTED(dim_state[state_name]), [Total Revenue], , DESC, Dense)
```

**Revenue (Top 10 States)** (Geography, format `#,0`): Revenue, only for the 10 best states (other states are empty and hidden in charts).

```dax
Revenue (Top 10 States) =
IF([State Rank] <= 10, [Total Revenue])
```

**Cumulative Revenue % (Top 20)** (Products, format `0.0%`): Pareto: running share of revenue when categories are sorted from high to low (first 20 categories).

```dax
Cumulative Revenue % (Top 20) =
VAR currentRevenue = [Total Revenue]
VAR allCategories = ALLSELECTED(dim_product[category])
VAR cumulative = SUMX(FILTER(allCategories, [Total Revenue] >= currentRevenue), [Total Revenue])
VAR total = SUMX(allCategories, [Total Revenue])
RETURN
    IF([Category Rank] <= 20, DIVIDE(cumulative, total))
```

### Table `fact_orders`

**Average Review Score** (Quality, format `0.00`): Average review score (1 to 5).

```dax
Average Review Score =
AVERAGE(fact_orders[review_score])
```

**Late Delivery Rate** (Quality, format `0.0%`): Share of delivered orders that arrived after the estimated date.

```dax
Late Delivery Rate =
AVERAGE(fact_orders[late_flag])
```

**Average Delivery Days** (Quality, format `0.0`): Days from purchase to delivery.

```dax
Average Delivery Days =
AVERAGE(fact_orders[delivery_days])
```

**Avg Review by Delay** (Quality, format `0.00`): Average review score of delivered orders (empty for orders that were not delivered).

```dax
Avg Review by Delay =
CALCULATE(AVERAGE(fact_orders[review_score]), fact_orders[delay_bucket_order] <= 5)
```

**Low Review Share by Delay** (Quality, format `0.0%`): Share of reviews with score 1 or 2, delivered orders only.

```dax
Low Review Share by Delay =
CALCULATE(AVERAGE(fact_orders[low_review_flag]), fact_orders[delay_bucket_order] <= 5)
```

**Active Customers** (Customers, format `#,0`): Customers (customer_unique_id) with at least one valid order in scope.

```dax
Active Customers =
DISTINCTCOUNT(fact_orders[customer_key])
```

**New Customers** (Customers, format `#,0`): Customers whose first order month is inside the selected months (same rule as SQL Q9).

```dax
New Customers =
VAR firstMonth = MIN(dim_date[month_start])
VAR lastMonth = MAX(dim_date[month_start])
RETURN
    CALCULATE(
        DISTINCTCOUNT(fact_orders[customer_key]),
        FILTER(
            ALL(dim_customer[first_order_month]),
            dim_customer[first_order_month] >= firstMonth && dim_customer[first_order_month] <= lastMonth
        )
    )
```

**Repeat Customers** (Customers, format `#,0`): Active customers who first bought in an earlier month (same rule as SQL Q9).

```dax
Repeat Customers =
[Active Customers] - [New Customers]
```

**Returning Customer % (period)** (Customers, format `0.0%`): Share of active customers who first bought earlier (SQL Q9 repeat_customer_pct).

```dax
Returning Customer % (period) =
DIVIDE([Repeat Customers], [Active Customers])
```

**Customers with 2+ Orders** (Customers, format `#,0`): Customers with 2 or more valid orders in the whole data (SQL Q10 repeat_customers when nothing is filtered).

```dax
Customers with 2+ Orders =
CALCULATE(DISTINCTCOUNT(fact_orders[customer_key]), dim_customer[order_count] >= 2)
```

**One-time Customers** (Customers, format `#,0`): Customers with exactly one valid order (SQL Q10 customers_with_1_order when nothing is filtered).

```dax
One-time Customers =
CALCULATE(DISTINCTCOUNT(fact_orders[customer_key]), dim_customer[order_count] = 1)
```

**Repeat Customer %** (Customers, format `0.0%`): Share of customers with 2 or more valid orders in the whole data (SQL Q10 repeat_purchase_rate_pct when nothing is filtered).

```dax
Repeat Customer % =
DIVIDE(
    CALCULATE(DISTINCTCOUNT(fact_orders[customer_key]), dim_customer[order_count] >= 2),
    [Active Customers]
)
```

### Table `cohort_retention`

**Cohort Retention %** (Customers, format `0.00%`): Customers of the cohort who ordered again in the month, as a share of the cohort (SQL Q11).

```dax
Cohort Retention % =
DIVIDE(SUM(cohort_retention[active_customers]), SUM(cohort_retention[cohort_size]))
```

## Model notes

- `dim_date` is the date table (marked as date table, complete years 2016 to 2018). `analysis_flag` = 1 for the full months 2017-01 to 2018-08.
- Filters flow like this: `dim_date`, `dim_state` -> `dim_customer` -> `fact_orders` -> `fact_order_items`, and `dim_product` -> `fact_order_items`.
- The category slicer filters revenue and orders (`fact_order_items`). It does not filter review, delivery and customer measures (`fact_orders`).
- `cohort_retention` has no relationships. The date, category and state slicers do not change the cohort matrix (it is all-time, from Q11).
- Monthly charts have a visual-level filter `analysis_flag = 1`, so the incomplete months (2016, 2018-09) are not drawn.
