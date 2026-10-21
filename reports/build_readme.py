"""Write README.md. Numbers come from the result files of the notebooks (reports/*.json) and the SQL outputs.

Run from the project root:  .venv\\Scripts\\python reports\\build_readme.py
(Run reports/build_insights_report.py first or at least have the three JSON files.)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reports"))
import build_insights_report as rep  # noqa: E402  (re-uses the findings and recommendations text; does not build the PDF)

README = ROOT / "README.md"
eda, stats, fc = rep.eda, rep.stats, rep.fc
tt, an, ch = stats["welch_ttest_real"], stats["anova_real"], stats["chi_square_real"]
pr, ab = stats["probability_real"], stats["ab_test_SIMULATED"]
n0, n1, n2 = rep.n0, rep.n1, rep.n2

# keep the table of the 15 SQL queries that already exists in the README
old = README.read_text(encoding="utf-8")
all_lines = old.splitlines()
start = next(i for i, ln in enumerate(all_lines) if ln.startswith("| # | Query"))
table_lines = []
for ln in all_lines[start:]:
    if not ln.startswith("|"):
        break
    table_lines.append(ln)
sql_table = "\n".join(table_lines)
assert len(table_lines) == 17, len(table_lines)   # header + separator + 15 queries


def strip_tags(text):
    return re.sub(r"<[^>]+>", "", text).replace("&bull;", "-")


findings = "\n".join(f"{i}. **{title}.** {text}" for i, (num, title, text) in enumerate(rep.findings, start=1))
recs = "\n".join(f"{i}. **{t}** (finding {links}). {text}" for i, (t, links, text) in enumerate(rep.recs, start=1))
limits = "\n".join(f"- {strip_tags(x)}" for x in rep.limits)
best = fc["best_model_by_rolling_mape"]
roll = fc["rolling_backtest"]

text = f"""# Ecommerce_Sales_Analytics

**An end-to-end data analyst project on about 100,000 real e-commerce orders: pipeline, cleaning, SQL, statistics, forecast, Excel, Power BI and a manager report.**

**Business question:** where does the marketplace grow, who buys, and what hurts customer satisfaction?
Answer in one line: revenue grew fast in 2017 and then flattened, almost nobody buys twice ({eda['repeat_purchase_rate_pct']:.2f}% of customers),
and late deliveries are the biggest driver of bad reviews ({n1(eda['low_review_pct_late'])}% low reviews for late orders vs {n1(eda['low_review_pct_on_time'])}% for on-time orders).

**Read the 2-page summary for managers: [reports/insights_report.pdf](reports/insights_report.pdf).**

| Power BI dashboard (3 pages) | |
|---|---|
| ![Sales overview](screenshots/powerbi_01_sales_overview.png) | ![Customers](screenshots/powerbi_02_customers.png) |
| ![Products and delivery](screenshots/powerbi_03_products_delivery.png) | |

## Part 2 of my e-commerce data project

This repository is the analysis part. The data engineering part is my pipeline repository
**[Enterprise_Data_Analysis](https://github.com/Vaibhavpisute/Enterprise_Data_Analysis)** (PostgreSQL, PySpark, MinIO and Hive in Docker).
The Olist data went through that pipeline first, and then I analysed its output:

```
Olist CSV files
   -> PostgreSQL (olist_db)                                   pipeline_ingest/01_load_olist_to_postgres.py
   -> PySpark job: cast types, remove duplicates, join        pipeline_ingest/02_olist_spark_job.py (runs in the pipeline's Airflow container)
   -> Parquet in MinIO + Hive tables (database "olist")
   -> export to data/raw/pipeline_output/                     pipeline_ingest/03_export_from_minio.py
   -> cleaning with pandas, star schema in PostgreSQL         notebooks/01_data_cleaning.ipynb  (analytics_db)
   -> 15 SQL queries                                          sql/
   -> EDA, statistics, A/B test (simulated), forecast         notebooks/02 to 04
   -> Excel report and Power BI dashboard                     excel/, powerbi/
   -> insights report (PDF)                                   reports/insights_report.pdf
```

## Tools used

PostgreSQL 16, PySpark 3.5 (local mode), MinIO, Hive, Apache Airflow and Docker (from the pipeline) | Python 3.12 with pandas, NumPy, SciPy,
statsmodels, scikit-learn, matplotlib, SQLAlchemy, openpyxl, pywin32, reportlab | SQL (window functions, CTEs, cohort and RFM logic) |
Microsoft Excel (formulas, XLOOKUP, Power Query, PivotTables, slicers) | Power BI Desktop (TMDL model, DAX, PBIR report) | Git.

## Key insights

All numbers come from the SQL results and the notebooks in this repository.
Revenue means item price without freight, for valid sales (not canceled or unavailable).

{findings}

| | |
|---|---|
| ![Monthly revenue and orders](screenshots/eda_01_monthly_revenue_orders.png) | ![Delivery delay vs review score](screenshots/eda_06_delivery_vs_review.png) |
| ![Category Pareto](screenshots/eda_03_category_pareto.png) | ![Cohort retention](screenshots/eda_05_cohort_retention.png) |

### Recommendations

{recs}

## The 15 SQL queries

Each file starts with the business question, the approach and where it is used later. Results are in `sql/outputs/`.
`sql/check_sql_vs_pandas.py` compares Q1 and five other queries with pandas (all checks match).

{sql_table}

## Statistics and A/B test

Details, assumptions and conclusions are in [notebooks/03_statistics_ab_test.ipynb](notebooks/03_statistics_ab_test.ipynb).
All tests use alpha = 0.05 and report an effect size, because with about 100,000 orders almost every difference is "significant".

| Test | Data | Result |
|---|---|---|
| Welch t-test: review score, on-time vs late | real | On-time orders score {n2(tt['difference'])} points higher ({n2(tt['mean_on_time'])} vs {n2(tt['mean_late'])}), 95% CI {n2(tt['ci95_low'])} to {n2(tt['ci95_high'])}, Cohen's d = {n2(tt['cohen_d'])} (large) |
| ANOVA and Kruskal-Wallis: order value by payment type | real | Assumptions fail (skewed data), Kruskal-Wallis is used. Types differ, but the effect is very small (eta squared {an['eta_squared']:.4f}) |
| Chi-square: RFM segment vs region | real | Significant, but Cramer's V = {ch['cramers_v']:.3f} (very small): region does not predict the segment |
| Probabilities | real | P(customer buys again) = {100 * pr['p_buy_again']:.2f}%. P(low review given late) = {100 * pr['p_low_given_late']:.2f}% vs {100 * pr['p_low_given_on_time']:.2f}% when on time (risk ratio {n2(pr['risk_ratio'])}) |
| **A/B test: free vs paid shipping** | **SIMULATED** | **SIMULATED data, not real customers** (fixed seed {ab['seed']}, assumed base rate {100 * ab['assumed_base_rate']:.1f}%). Needs {n0(ab['sample_size_per_group'])} visitors per group for a +{100 * ab['assumed_mde']:.1f} point effect. Simulated result: {100 * ab['rate_a']:.2f}% vs {100 * ab['rate_b']:.2f}%, lift {n1(ab['lift_pct'])}%, p = {ab['p_value']:.2g}. Design check with 5,000 repeated simulated experiments: power {100 * ab['simulated_power']:.1f}%, false positives {100 * ab['simulated_false_positive_rate']:.1f}% |

## Forecast

[notebooks/04_forecast.ipynb](notebooks/04_forecast.ipynb) forecasts monthly revenue for the 3 months after the data
({fc['forecast_months'][0]} to {fc['forecast_months'][-1]}). It uses the {fc['months_used']} full months ({fc['first_month']} to {fc['last_month']}).
A time-based split (last 3 months as test) and a rolling backtest compare a 3-month moving average, a linear regression (trend and month pattern) and Holt smoothing.
**Result:** the simple moving average wins (rolling backtest MAPE {n1(roll[best]['mape_pct'])}%, against {n1(roll['Linear regression']['mape_pct'])}% for regression
and {n1(roll['Holt (damped trend)']['mape_pct'])}% for Holt), because growth was flat in 2018. Forecast: about {n0(fc['forecast_per_month'][0])} per month
(range {n0(fc['forecast_low'][0])} to {n0(fc['forecast_high'][0])}). It is a method demo: short history, no holiday information.

![Forecast](screenshots/forecast_01_actual_vs_predicted.png)

## Excel report and Power BI dashboard

- **Excel:** [excel/sales_report.xlsx](excel/sales_report.xlsx): KPIs with real formulas and conditional formatting, RFM segments with XLOOKUP,
  Power Query queries (the data folder is the named cell `DataFolder`), PivotTables with slicers, PivotCharts. Built and checked with Excel automation,
  see [excel/EXCEL_STEPS.md](excel/EXCEL_STEPS.md).
- **Power BI:** [powerbi/EcommerceSales.pbip](powerbi/EcommerceSales.pbip): a Power BI Project (TMDL model with a date table, 7 relationships and 28 DAX measures, PBIR report with 3 pages).
  The saved file [powerbi/dashboard.pbix](powerbi/dashboard.pbix) (6.4 MB, data included) opens directly. The model CSV files (`powerbi/data/`) are not in git. See [powerbi/POWERBI_STEPS.md](powerbi/POWERBI_STEPS.md) to regenerate it, refresh and check the numbers. DAX list: [powerbi/DAX_MEASURES.md](powerbi/DAX_MEASURES.md).

| | |
|---|---|
| ![Excel KPIs](screenshots/excel_01_kpi_table.png) | ![Excel PivotTables and slicers](screenshots/excel_06_pivot_slicers.png) |

## Limits

{limits}

## Data source and credit

**Brazilian E-Commerce Public Dataset by Olist** ([Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)). Real, anonymised orders (2016 to 2018).
Credit: Olist, who released the dataset. Licence: **CC BY-NC-SA 4.0** (non-commercial use, share alike, give credit), so this project is for learning and portfolio use.
More details and row counts: [data/DATA_SOURCE.md](data/DATA_SOURCE.md). The A/B test in this project is simulated and is always labelled SIMULATED.

## How to run

Needs: Windows, Docker Desktop, Python 3.12, a Kaggle account (for the download). Excel and Power BI Desktop are only needed for the last two steps.

1. **Set up Python:** `py -3.12 -m venv .venv`, then `.venv\\Scripts\\pip install -r requirements.txt`.
2. **Settings:** copy `.env.example` to `.env` and fill in the values (PostgreSQL and MinIO of the pipeline's Docker containers). `.env` is never committed.
3. **Start the pipeline containers** (project `sales-demo` of the pipeline repository): `docker compose up -d` in its `local_demo` folder.
4. **Get the data through the pipeline:** put your Kaggle token in `C:\\Users\\<you>\\.kaggle\\kaggle.json`, then follow [pipeline_ingest/README.md](pipeline_ingest/README.md)
   (download, load into PostgreSQL, run the Spark job, export from MinIO).
5. **Clean and load the star schema:** run `notebooks/01_data_cleaning.ipynb` (creates `data/processed/` and fills `analytics_db`).
6. **SQL:** `.venv\\Scripts\\python sql\\run_all_queries.py`, then `.venv\\Scripts\\python sql\\check_sql_vs_pandas.py`.
7. **Notebooks** (02, 03, 04): `.venv\\Scripts\\jupyter nbconvert --to notebook --execute --inplace notebooks\\<name>.ipynb` for each notebook.
   They also write `reports/eda_results.json`, `reports/stats_results.json` and `reports/forecast_results.json`.
8. **Excel:** `python excel\\build_workbook.py`, `python excel\\add_excel_features.py`, `python excel\\check_and_export.py` (see `excel/EXCEL_STEPS.md`).
9. **Power BI:** `python powerbi\\export_model_data.py`, then open `powerbi\\EcommerceSales.pbip` (see `powerbi/POWERBI_STEPS.md`).
10. **Report and README:** `python reports\\build_insights_report.py`, then `python reports\\build_readme.py`.
11. **Checks before publishing:** `python reports\\check_numbers.py` recomputes every number of this README and of the PDF (needs the PostgreSQL container) and writes
    `reports/number_check.md`.
12. Stop the containers: `docker compose stop`.

`requirements.txt` includes `pywin32`, which is only needed (and only installs) on Windows, for the Excel automation.

## Folder structure

```
Ecommerce_Sales_Analytics/
|-- pipeline_ingest/   Olist load, PySpark job, export from MinIO, run steps
|-- data/              DATA_SOURCE.md (raw and processed data are not committed)
|-- sql/               q01 to q15 queries, run_all_queries.py, check_sql_vs_pandas.py, outputs/ (results as CSV)
|-- notebooks/         01_data_cleaning, 02_eda, 03_statistics_ab_test, 04_forecast (all executed)
|-- src/               db.py, plots.py, helpers.py
|-- excel/             sales_report.xlsx, build and check scripts, EXCEL_STEPS.md
|-- powerbi/           EcommerceSales.pbip (TMDL + PBIR), DAX_MEASURES.md, POWERBI_STEPS.md, theme.json, export and build scripts
|-- screenshots/       charts, Excel and Power BI images used in this README
|-- reports/           insights_report.pdf, result files (json, csv), scripts that build the report and this README
`-- requirements.txt
```
"""
README.write_text(text, encoding="utf-8")
print(f"saved README.md ({len(text.splitlines())} lines, {len(table_lines)} table lines kept from the SQL table)")
