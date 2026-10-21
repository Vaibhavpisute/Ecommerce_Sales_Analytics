"""Number check: every number in the README and the PDF report must match a query or notebook result.

For each claim the script
  1. takes the value that the documents use (from reports/*.json, written by the notebooks),
  2. recomputes it independently (live SQL on analytics_db, the SQL result files, pandas, or a fresh simulation),
  3. formats both the way the documents show them and compares the text,
  4. checks that the text really appears in README.md or in the PDF text.
Then it lists every other number in the key sections of the documents that is not covered by a claim, for a manual look.
Writes reports/number_check.md. Exit code 1 if a claim does not match.

Needs the PostgreSQL container (analytics_db). Run from the project root:  .venv\\Scripts\\python reports\\check_numbers.py
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "reports"))
from src.db import get_engine  # noqa: E402
from src.helpers import STATE_TO_REGION  # noqa: E402
import build_insights_report as rep  # noqa: E402  (only used for the PDF text strings)

SQL = ROOT / "sql" / "outputs"
eda = json.loads((ROOT / "reports" / "eda_results.json").read_text(encoding="utf-8"))
st = json.loads((ROOT / "reports" / "stats_results.json").read_text(encoding="utf-8"))
fc = json.loads((ROOT / "reports" / "forecast_results.json").read_text(encoding="utf-8"))
readme = (ROOT / "README.md").read_text(encoding="utf-8")

pdf_text = " ".join([rep.question, *[f"{v} {l}" for v, l in rep.kpis], *[f"{t} {x}" for _, t, x in rep.findings],
                     *[f"{t} {x}" for t, _, x in rep.recs], rep.outlook, *rep.limits])
pdf_text = re.sub(r"<[^>]+>", "", pdf_text)
docs = readme + "\n" + pdf_text


def q(prefix):
    return pd.read_csv(next(SQL.glob(f"{prefix}_*.csv")))


eng = get_engine()


def db(sql):
    with eng.connect() as c:
        return c.execute(text(sql)).fetchone()


def n0(x): return f"{x:,.0f}"
def n1(x): return f"{x:,.1f}"
def n2(x): return f"{x:,.2f}"
def n3(x): return f"{x:.3f}"
def n4(x): return f"{x:.4f}"
def p2(x): return f"{x:.2f}%"


claims = []   # (name, format function, value used in documents, independent value, source)


def claim(name, fmt, used, independent, source):
    claims.append((name, fmt, used, independent, source))


# ---------------------------------------------------------------- independent sources
rev, orders_n, customers_n = db("select sum(items_value), count(*), count(distinct customer_unique_id) from fact_orders where is_valid_sale")
rev, orders_n, customers_n = float(rev), int(orders_n), int(customers_n)
repeat_n = int(db("select count(*) from (select customer_unique_id from fact_orders where is_valid_sale group by 1 having count(*) >= 2) t")[0])
freight_pct = float(db("select 100 * avg(freight_value) / avg(items_value) from fact_orders where is_valid_sale")[0])
q2, q3, q5, q7 = q("q02"), q("q03"), q("q05"), q("q07")
q9, q10, q11, q12, q14, q15 = q("q09"), q("q10"), q("q11"), q("q12"), q("q14"), q("q15")
full = q2[q2.in_analysis_period].reset_index(drop=True)

# delivered orders with a review, by lateness (live SQL)
g = db("""select count(*) filter (where o.delay_days > 0), count(*) filter (where o.delay_days <= 0),
                 avg(r.review_score) filter (where o.delay_days > 0), avg(r.review_score) filter (where o.delay_days <= 0),
                 stddev_samp(r.review_score) filter (where o.delay_days > 0), stddev_samp(r.review_score) filter (where o.delay_days <= 0),
                 count(*) filter (where o.delay_days > 0 and r.review_score <= 2), count(*) filter (where o.delay_days <= 0 and r.review_score <= 2)
          from fact_orders o join fact_reviews r on r.order_id = o.order_id
          where o.order_status = 'delivered' and o.delay_days is not null""")
n_late, n_on, m_late, m_on, s_late, s_on, low_late, low_on = [float(x) for x in g]
sp = np.sqrt(((n_on - 1) * s_on ** 2 + (n_late - 1) * s_late ** 2) / (n_on + n_late - 2))
cohen_d = (m_on - m_late) / sp
rr = (low_late / n_late) / (low_on / n_on)

# ---------------------------------------------------------------- claims: headline numbers
claim("Revenue (BRL, shown in millions)", lambda x: f"{x / 1e6:.2f}M", eda["revenue_total"], rev, "SQL on fact_orders")
claim("Revenue (BRL, exact)", n2, eda["revenue_total"], rev, "SQL on fact_orders")
claim("Orders (valid sales)", n0, eda["orders_total"], orders_n, "SQL on fact_orders")
claim("Customers with a valid order", n0, eda["customers_with_valid_order"], customers_n, "SQL on fact_orders")
claim("Average order value", n2, eda["aov_all_orders"], rev / orders_n, "SQL: revenue / orders")
claim("Customers who bought again (count)", n0, eda["repeat_customers"], repeat_n, "SQL on fact_orders")
claim("Repeat purchase rate", p2, eda["repeat_purchase_rate_pct"], 100 * repeat_n / customers_n, "SQL on fact_orders")
claim("Repeat rate in the statistics notebook", p2, 100 * st["probability_real"]["p_buy_again"], 100 * repeat_n / customers_n, "SQL on fact_orders")
# ---------------------------------------------------------------- trend and growth (Q2, Q3)
claim("Revenue first full month", n0, eda["first_full_month"]["revenue"], full.revenue.iloc[0], "Q2")
claim("Revenue last full month", n0, eda["last_full_month"]["revenue"], full.revenue.iloc[-1], "Q2")
claim("Peak month revenue", n0, eda["peak_month"]["revenue"], full.revenue.max(), "Q2")
claim("Peak month name", str, eda["peak_month"]["month"], full.loc[full.revenue.idxmax(), "year_month"], "Q2")
q3i = q3.set_index("year_month")
claim("Average MoM growth 2017 (Feb-Dec)", n1, eda["avg_mom_growth_2017_pct"], q3i.loc["2017-02":"2017-12", "mom_growth_pct"].mean(), "Q3")
claim("Average MoM growth 2018 (Jan-Aug)", n1, eda["avg_mom_growth_2018_pct"], q3i.loc["2018-01":"2018-08", "mom_growth_pct"].mean(), "Q3")
# ---------------------------------------------------------------- customers (Q9, Q11, Q12)
claim("Cohort month-1 retention average", p2, eda["cohort_month1_retention_avg_pct"], q11[q11.month_index == 1].retention_pct.mean(), "Q11")
claim("Revenue share from customers in their first month", n1, eda["new_customer_revenue_share_pct"],
      100 * q9.revenue_from_new.sum() / (q9.revenue_from_new.sum() + q9.revenue_from_repeat.sum()), "Q9")
seg = q12.segment.value_counts()
claim("Segment New Customers (count)", n0, int(seg["New Customers"]), int((q12.segment == "New Customers").sum()), "Q12")
claim("Champions + Loyal + At Risk (count)", n0, int(seg["Champions"] + seg["Loyal"] + seg["At Risk"]),
      int(q12.segment.isin(["Champions", "Loyal", "At Risk"]).sum()), "Q12")
# ---------------------------------------------------------------- delivery and reviews (Q14, live SQL)
q14g = q14[q14.level == "late_vs_on_time"].set_index("group_name")
claim("Late share of delivered, reviewed orders", n1, eda["late_share_of_delivered_reviewed_pct"], 100 * n_late / (n_late + n_on), "SQL on fact_orders and fact_reviews")
claim("Late share (Q14 counts)", n1, eda["late_share_of_delivered_reviewed_pct"],
      100 * q14g.loc["Late", "orders"] / q14g.orders.sum(), "Q14")
claim("Low review % when late", n1, eda["low_review_pct_late"], 100 * low_late / n_late, "SQL")
claim("Low review % on time", n1, eda["low_review_pct_on_time"], 100 * low_on / n_on, "SQL")
claim("Average score late", n2, eda["avg_score_late"], m_late, "SQL")
claim("Average score on time", n2, eda["avg_score_on_time"], m_on, "SQL")
claim("Risk ratio late vs on time", n1, st["probability_real"]["risk_ratio"], rr, "SQL counts")
claim("Risk ratio (two decimals)", n2, st["probability_real"]["risk_ratio"], rr, "SQL counts")
claim("Cohen's d (Welch t-test)", n2, st["welch_ttest_real"]["cohen_d"], cohen_d, "SQL mean, sd, n")
claim("Mean difference on time minus late", n2, st["welch_ttest_real"]["difference"], m_on - m_late, "SQL")
claim("P(low review | late)", p2, 100 * st["probability_real"]["p_low_given_late"], 100 * low_late / n_late, "SQL")
claim("P(low review | on time)", p2, 100 * st["probability_real"]["p_low_given_on_time"], 100 * low_on / n_on, "SQL")
# ---------------------------------------------------------------- categories, states, timing (Q5, Q7, Q15)
claim("Categories needed for 80% of revenue", n0, eda["categories_for_80pct"], int(q7.in_top_80pct.sum()), "Q7")
claim("Number of categories", n0, eda["categories_total"], len(q7), "Q7")
claim("Top 3 categories share", n1, eda["top3_categories_share_pct"], q7.revenue_share_pct.head(3).sum(), "Q7")
claim("Top 3 category names", lambda x: ", ".join(c.replace("_", " ") for c in x), eda["top3_categories"], list(q7.category_en.head(3)), "Q7")
claim("Unknown category revenue share", n1, eda["unknown_category_revenue_share_pct"],
      float(q7.loc[q7.category_en == "unknown", "revenue_share_pct"].iloc[0]), "Q7")
states = q15[q15.level == "State"].sort_values("revenue", ascending=False)
tot = q15[q15.level == "All orders"].revenue.iloc[0]
claim("Top 3 states", lambda x: ", ".join(x), eda["top3_states"], list(states.state.head(3)), "Q15")
claim("Top 3 states share", n1, eda["top3_states_share_pct"], 100 * states.revenue.head(3).sum() / tot, "Q15")
claim("Top state share", n1, eda["top_state_share_pct"], 100 * states.revenue.iloc[0] / tot, "Q15")
claim("Orders 10:00-16:59 share", n1, eda["orders_10_to_16h_share_pct"], 100 * q5[q5.hour_of_day.between(10, 16)].orders.sum() / q5.orders.sum(), "Q5")
claim("Weekend order share", n1, eda["weekend_order_share_pct"], 100 * q5[q5.day_of_week >= 6].orders.sum() / q5.orders.sum(), "Q5")
claim("Busiest weekday", str, eda["busiest_weekday"], q5.groupby("day_name").orders.sum().idxmax(), "Q5")
claim("Quietest weekday", str, eda["quietest_weekday"], q5.groupby("day_name").orders.sum().idxmin(), "Q5")
claim("Freight as % of item value", n1, st["real_freight_context"]["freight_pct_of_items_value"], freight_pct, "SQL on fact_orders")
# ---------------------------------------------------------------- statistics recomputed from SQL and Q12
pay = pd.DataFrame(eng.connect().execute(text(
    "select main_payment_type t, count(*) n, sum(items_value) s, sum(items_value * items_value) s2 from fact_orders "
    "where is_valid_sale and main_payment_type is not null group by 1")).fetchall(), columns=["t", "n", "s", "s2"]).astype({"n": float, "s": float, "s2": float})
N, S, S2 = pay.n.sum(), pay.s.sum(), pay.s2.sum()
eta2 = (((pay.s ** 2) / pay.n).sum() - S ** 2 / N) / (S2 - S ** 2 / N)
claim("ANOVA eta squared", n4, st["anova_real"]["eta_squared"], eta2, "SQL sums by payment type")
tab = pd.crosstab(q12.segment, q12.customer_state.map(STATE_TO_REGION))
chi2, _, _, _ = stats.chi2_contingency(tab)
claim("Chi-square Cramer's V", n3, st["chi_square_real"]["cramers_v"], float(np.sqrt(chi2 / (tab.values.sum() * (min(tab.shape) - 1)))), "Q12 + region map")
# ---------------------------------------------------------------- simulated A/B test (fresh simulation with the stated assumptions)
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize, proportions_ztest

ab = st["ab_test_SIMULATED"]
effect = proportion_effectsize(ab["assumed_base_rate"] + ab["assumed_mde"], ab["assumed_base_rate"])
n_grp = int(np.ceil(NormalIndPower().solve_power(effect, alpha=0.05, power=0.8, ratio=1, alternative="two-sided")))
rng = np.random.default_rng(ab["seed"])
ca, cb = int(rng.binomial(n_grp, ab["assumed_base_rate"])), int(rng.binomial(n_grp, ab["assumed_base_rate"] + ab["assumed_mde"]))
z, pval = proportions_ztest([cb, ca], [n_grp, n_grp])
claim("SIMULATED: sample size per group", n0, ab["sample_size_per_group"], n_grp, "fresh power analysis")
claim("SIMULATED: conversion A", p2, 100 * ab["rate_a"], 100 * ca / n_grp, "fresh simulation, seed 42")
claim("SIMULATED: conversion B", p2, 100 * ab["rate_b"], 100 * cb / n_grp, "fresh simulation, seed 42")
claim("SIMULATED: lift", n1, ab["lift_pct"], 100 * (cb / ca - 1), "fresh simulation, seed 42")
claim("SIMULATED: p-value", lambda x: f"{x:.2g}", ab["p_value"], pval, "fresh simulation, seed 42")
# ---------------------------------------------------------------- forecast (Q4 and a fresh baseline backtest from Q2)
q4 = q("q04")
rev_m = full.revenue.to_numpy(float)
mapes = []
for k in range(10, len(rev_m) - 3 + 1):
    pred = rev_m[k - 3:k].mean()
    mapes.append(np.mean(np.abs(rev_m[k:k + 3] - pred) / rev_m[k:k + 3]) * 100)
claim("Forecast per month (baseline = last Q4 moving average)", n0, fc["forecast_per_month"][0], q4.moving_avg_3m.iloc[-1], "Q4")
claim("Baseline rolling backtest MAPE", n1, fc["rolling_backtest"]["Moving average (baseline)"]["mape_pct"], float(np.mean(mapes)), "fresh backtest on Q2")
claim("Forecast range low", n0, fc["forecast_low"][0], q4.moving_avg_3m.iloc[-1] * (1 - np.mean(mapes) / 100), "Q4 and backtest")
claim("Forecast range high", n0, fc["forecast_high"][0], q4.moving_avg_3m.iloc[-1] * (1 + np.mean(mapes) / 100), "Q4 and backtest")
claim("Number of full months used", n0, fc["months_used"], len(full), "Q2")

# ---------------------------------------------------------------- run the comparison
NOT_IN_DOCS = {"Revenue (BRL, exact)"}   # control number only: the documents show 13.49M
rows, failures = [], []
for name, fmt, used, indep, source in claims:
    used_s, indep_s = fmt(used), fmt(indep)
    match = used_s == indep_s
    in_docs = used_s in docs or (isinstance(used, float) and fmt(used).replace(",", "") in docs.replace(",", ""))
    if not match or (not in_docs and name not in NOT_IN_DOCS):
        failures.append(name)
    rows.append((name, used_s, indep_s, source, "OK" if match else "MISMATCH", "yes" if in_docs else "NOT FOUND"))

# values that are only quoted from notebook output (no independent recomputation here)
notebook_only = [
    ("Regression and Holt rolling-backtest MAPE", f"{fc['rolling_backtest']['Linear regression']['mape_pct']:.1f}% / {fc['rolling_backtest']['Holt (damped trend)']['mape_pct']:.1f}%",
     "notebooks/04_forecast.ipynb (re-executed in this run)"),
    ("A/B design check: simulated power / false positives", f"{100 * ab['simulated_power']:.1f}% / {100 * ab['simulated_false_positive_rate']:.1f}%",
     "notebooks/03_statistics_ab_test.ipynb (5,000 simulated experiments, fixed seed)"),
    ("Welch t-test CI of the difference", f"{st['welch_ttest_real']['ci95_low']:.2f} to {st['welch_ttest_real']['ci95_high']:.2f}", "notebooks/03_statistics_ab_test.ipynb"),
]

# ---------------------------------------------------------------- assumptions and rounded descriptions
nb3 = (ROOT / "notebooks" / "03_statistics_ab_test.ipynb").read_text(encoding="utf-8")
all_orders_n = int(db("select count(*) from fact_orders")[0])
extras = [
    ("SIMULATED assumption: base conversion rate", "3.0%", f"{100 * ab['assumed_base_rate']:.1f}%" == "3.0%" and "SIM_BASE_RATE = 0.030" in nb3,
     "stated assumption in notebook 03 (SIMULATED)"),
    ("SIMULATED assumption: minimum detectable effect", "+0.5 point", f"{100 * ab['assumed_mde']:.1f}" == "0.5" and "SIM_MDE = 0.005" in nb3,
     "stated assumption in notebook 03 (SIMULATED)"),
    ("Number of repeated simulated experiments", "5,000", "runs = 5000" in nb3, "notebook 03 code"),
    ("'About 100,000 orders'", "100,000", abs(all_orders_n - 100000) / 100000 < 0.01, f"rounded description of {all_orders_n:,} orders in fact_orders"),
]
for name, shown, ok, source in extras:
    rows.append((name, shown, "assumption / rounding confirmed" if ok else "NOT CONFIRMED", source, "OK" if ok else "MISMATCH", "yes" if shown.strip("+") in docs or shown.replace(" point", "") in docs else "NOT FOUND"))
    if not ok:
        failures.append(name)

# ---------------------------------------------------------------- numbers in the documents that no claim covers
claim_text = " ".join(str(r[1]) for r in rows) + " " + " ".join(r[1] for r in notebook_only)
claim_tokens = {t.replace(",", "").rstrip("%").rstrip(".") for t in re.findall(r"\d[\d,]*\.?\d*", claim_text)}
sections = []
head = readme.split("## Part 2")[0]
sections.append(head)
sections.append(readme.split("## Key insights")[1].split("## The 15 SQL queries")[0])
sections.append(readme.split("## Statistics and A/B test")[1].split("## Excel report")[0])
scan_text = "\n".join(sections + [pdf_text])
scan_text = re.sub(r"\(?\d{4}-\d{2}\)?", " ", scan_text)                    # months like 2017-01
scan_text = re.sub(r"!\[[^\]]*\]\([^)]*\)|\([^)]*\.(?:png|md|csv|pdf|ipynb|sql)\)", " ", scan_text)   # image and file links
scan_text = re.sub(r"\b\d{1,2}:\d{2}\b", " ", scan_text)                    # clock times
unmatched = []
for tok in re.findall(r"\d[\d,]*\.?\d*%?", scan_text):
    norm = tok.replace(",", "").rstrip("%").rstrip(".")
    if not norm or norm in claim_tokens:
        continue
    if re.fullmatch(r"\d{1,2}", norm) or re.fullmatch(r"20(1[6-8])", norm) or norm in {"100", "80", "95", "0.05"}:
        continue          # list numbers, finding numbers, the years of the data, 80% rule, alpha
    unmatched.append(tok)
unmatched = sorted(set(unmatched), key=lambda s: (len(s), s))

# ---------------------------------------------------------------- write the report
md = ["# Number check", "",
      "Every number that the README and the PDF use is recomputed from the live database (`analytics_db`), the SQL result files or a fresh simulation, "
      "formatted like the documents show it, compared, and searched in the document text.", "",
      f"**Result: {len(rows) - len(failures)} of {len(rows)} claims match and appear in the documents.**"
      + ("" if not failures else f" **Problems: {', '.join(failures)}**"), "",
      "| Claim | In documents | Recomputed | Source of the recomputation | Match | Found in README or PDF |", "|---|---|---|---|---|---|"]
md += [f"| {a} | {b} | {c} | {d} | {e} | {f} |" for a, b, c, d, e, f in rows]
md += ["", "## Quoted from notebook output (not recomputed here)", "", "| Value | Number | Source |", "|---|---|---|"]
md += [f"| {a} | {b} | {c} |" for a, b, c in notebook_only]
md += ["", "## Other numbers in the key sections that no claim covers (manual look)", "",
       ", ".join(unmatched) if unmatched else "None."]
(ROOT / "reports" / "number_check.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print(f"{len(rows) - len(failures)} of {len(rows)} claims match and appear in the documents")
print("uncovered numbers for a manual look:", unmatched if unmatched else "none")
if failures:
    print("PROBLEMS:", failures)
    sys.exit(1)
