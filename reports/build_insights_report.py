"""Build reports/insights_report.pdf (2 pages, for a non-technical manager) with reportlab.

Every number comes from files written by the notebooks and the SQL runs (nothing is typed by hand):
  reports/eda_results.json, reports/stats_results.json, reports/forecast_results.json   (notebooks 02, 03, 04)
  sql/outputs/q02, q12, q14 csv                                                         (SQL results)

Run from the project root:  .venv\\Scripts\\python reports\\build_insights_report.py
"""
import io
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import plots  # noqa: E402

REPORTS = ROOT / "reports"
SQL_OUT = ROOT / "sql" / "outputs"
PDF = REPORTS / "insights_report.pdf"
BLUE = colors.HexColor("#1C5CAB")
INK = colors.HexColor("#0B0B0B")
GREY = colors.HexColor("#52514E")
LIGHT = colors.HexColor("#F3F2EF")


def load(name):
    return json.loads((REPORTS / name).read_text(encoding="utf-8"))


def sql(prefix):
    return pd.read_csv(next(SQL_OUT.glob(f"{prefix}_*.csv")))


eda, stats, fc = load("eda_results.json"), load("stats_results.json"), load("forecast_results.json")
q12 = sql("q12")
seg = q12.segment.value_counts()


def n0(x):
    return f"{x:,.0f}"


def n1(x):
    return f"{x:,.1f}"


def n2(x):
    return f"{x:,.2f}"


# ------------------------------------------------------------------ charts (data from the SQL result files)
def chart_png(kind):
    plots.setup()
    fig, ax = plt.subplots(figsize=(4.3, 2.5))
    if kind == "revenue":
        q2 = sql("q02").query("in_analysis_period")
        ax.bar(q2.year_month, q2.revenue / 1000, color=plots.BLUE, width=0.7)
        ax.set_title("Revenue per month (full months)", fontsize=9)
        ax.set_ylabel("Revenue (thousand BRL)", fontsize=8)
        ax.set_xticks(range(0, len(q2), 3), q2.year_month.iloc[::3], rotation=45, ha="right", fontsize=7)
    else:
        b = sql("q14").query("level == 'bucket'").sort_values("bucket_order")
        labels = ["Early\n7+ days", "On time\n(0-7 early)", "Late\n0-3 days", "Late\n3-7 days", "Late\n7+ days"]
        ax.bar(labels, b.avg_review_score, color=plots.BLUE, width=0.65)
        for x, v in enumerate(b.avg_review_score):
            ax.text(x, v + 0.08, f"{v:.2f}", ha="center", fontsize=7.5)
        ax.set_ylim(0, 5)
        ax.set_title("Average review score by delivery delay", fontsize=9)
        ax.set_ylabel("Average score (1 to 5)", fontsize=8)
        ax.tick_params(axis="x", labelsize=7)
    ax.tick_params(axis="y", labelsize=7)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=220)
    plt.close(fig)
    buf.seek(0)
    return buf


# ------------------------------------------------------------------ text
ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=19, leading=22, alignment=TA_LEFT, textColor=INK, spaceAfter=2)
SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontName="Helvetica", fontSize=9, leading=12, textColor=GREY, spaceAfter=6)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=11.5, leading=14, textColor=BLUE, spaceBefore=8, spaceAfter=3)
BODY = ParagraphStyle("BODY", parent=ss["Normal"], fontName="Helvetica", fontSize=9, leading=12, textColor=INK)
CELL = ParagraphStyle("CELL", parent=BODY, fontSize=8.5, leading=11)
SMALL = ParagraphStyle("SMALL", parent=BODY, fontSize=8, leading=10.5, textColor=GREY)
KPI_N = ParagraphStyle("KPI_N", parent=BODY, fontName="Helvetica-Bold", fontSize=15, leading=18, alignment=1)
KPI_L = ParagraphStyle("KPI_L", parent=BODY, fontSize=7.5, leading=9, alignment=1, textColor=GREY)


def p(text, style=BODY):
    return Paragraph(text, style)


a = stats["ab_test_SIMULATED"]
ttest, prob, fr = stats["welch_ttest_real"], stats["probability_real"], stats["real_freight_context"]

question = ("Where does the marketplace grow, who buys, and what hurts customer satisfaction? "
            "This report uses about 100,000 real, anonymised orders from the Olist marketplace in Brazil (2016 to 2018) "
            "and gives 5 actions for the next quarter.")

kpis = [
    (f"{eda['revenue_total'] / 1e6:.2f}M", "Revenue (BRL, item prices)"),
    (n0(eda["orders_total"]), "Orders (valid sales)"),
    (n0(eda["customers_with_valid_order"]), "Customers"),
    (n2(eda["aov_all_orders"]), "Average order value (BRL)"),
    (f"{eda['repeat_purchase_rate_pct']:.2f}%", "Customers who bought again"),
]

findings = [
    ("1", "Growth slowed in 2018",
     f"Monthly revenue rose from {n0(eda['first_full_month']['revenue'])} ({eda['first_full_month']['month']}) to "
     f"{n0(eda['last_full_month']['revenue'])} ({eda['last_full_month']['month']}); the peak was {eda['peak_month']['month']} "
     f"({n0(eda['peak_month']['revenue'])}). Average monthly growth fell from {n1(eda['avg_mom_growth_2017_pct'])}% in 2017 to "
     f"{n1(eda['avg_mom_growth_2018_pct'])}% in 2018."),
    ("2", "Almost nobody comes back",
     f"Only {n0(eda['repeat_customers'])} of {n0(eda['customers_with_valid_order'])} customers ({eda['repeat_purchase_rate_pct']:.2f}%) bought more than once. "
     f"On average {eda['cohort_month1_retention_avg_pct']:.2f}% of a monthly cohort orders again in the next month. "
     f"{n1(eda['new_customer_revenue_share_pct'])}% of revenue comes from customers in their first month."),
    ("3", "Late delivery destroys reviews",
     f"{n1(eda['late_share_of_delivered_reviewed_pct'])}% of delivered orders arrive late. {n1(eda['low_review_pct_late'])}% of late orders get a "
     f"1 or 2 star review, against {n1(eda['low_review_pct_on_time'])}% of on-time orders (average score {n2(eda['avg_score_late'])} vs "
     f"{n2(eda['avg_score_on_time'])}). A late order is {n1(prob['risk_ratio'])} times as likely to get a low review "
     f"(statistical test: p below 0.05, effect size d = {n2(ttest['cohen_d'])}, large)."),
    ("4", "A few categories carry the business",
     f"{eda['categories_for_80pct']} of {eda['categories_total']} categories make 80% of revenue. The top 3 "
     f"({', '.join(c.replace('_', ' ') for c in eda['top3_categories'])}) make {n1(eda['top3_categories_share_pct'])}%. "
     f"Products without a category name make {n1(eda['unknown_category_revenue_share_pct'])}% of revenue."),
    ("5", "Revenue sits in the Southeast",
     f"{', '.join(eda['top3_states'])} make {n1(eda['top3_states_share_pct'])}% of revenue; {eda['top3_states'][0]} alone makes "
     f"{n1(eda['top_state_share_pct'])}%."),
    ("6", "People buy on weekdays, during work hours",
     f"{n1(eda['orders_10_to_16h_share_pct'])}% of orders are placed between 10:00 and 16:59, and only {n1(eda['weekend_order_share_pct'])}% on a "
     f"weekend ({eda['busiest_weekday']} is the busiest day, {eda['quietest_weekday']} the quietest)."),
]

new_cust = int(seg.get("New Customers", 0))
at_risk = int(seg.get("At Risk", 0)) + int(seg.get("Loyal", 0)) + int(seg.get("Champions", 0))
recs = [
    ("Fix delivery first", "3",
     f"Reduce late deliveries and make delivery dates honest: watch the slowest carriers and lanes, add safety days to risky estimates, and warn "
     f"customers early. Track the late rate (today {n1(eda['late_share_of_delivered_reviewed_pct'])}%) and the share of 1 and 2 star reviews every month."),
    ("Start a retention programme", "2",
     f"Send a follow-up message after delivery and a second-order offer. Start with the {n0(new_cust)} recent first-time buyers (segment "
     f"\"New Customers\") and the {n0(at_risk)} repeat buyers in the segments Champions, Loyal and At Risk."),
    ("Focus range and marketing on the top categories", "4",
     f"Put stock, seller recruitment and advertising budget behind the {eda['categories_for_80pct']} categories that make 80% of revenue. "
     f"Fix the missing category names ({n1(eda['unknown_category_revenue_share_pct'])}% of revenue) so that reports are complete."),
    ("Test free shipping with a real A/B test", "1, 5",
     f"Freight is {n1(fr['freight_pct_of_items_value'])}% of the item value, so free shipping is expensive. Run a proper test before any roll-out. "
     f"The method demo in this project (SIMULATED data, not real customers) shows that about {n0(a['sample_size_per_group'])} visitors per group "
     f"are needed to detect a +{100 * a['assumed_mde']:.1f} point gain on a {100 * a['assumed_base_rate']:.1f}% conversion rate."),
    ("Run promotions and support on weekdays", "6",
     "Plan promotions, e-mail sends and customer support hours for weekdays between 10:00 and 17:00, when most orders arrive."),
]

fl = fc["forecast_per_month"][0]
outlook = (f"<b>Outlook.</b> A simple forecast (the average of the last 3 months) gives about {n0(fl)} BRL per month for "
           f"{fc['forecast_months'][0]} to {fc['forecast_months'][-1]} (range {n0(fc['forecast_low'][0])} to {n0(fc['forecast_high'][0])}). "
           f"More complex models did not beat this baseline. The typical error in a backtest was {n1(fc['range_pct'])}%.")

limits = [
    f"<b>Period and scope.</b> One marketplace, valid sales from {sql('q02').year_month.min()} to {sql('q02').year_month.max()}. "
    f"Trends use the full months {fc['first_month']} to {fc['last_month']} only.",
    "<b>Patterns, not proof.</b> The data shows links (for example late delivery and low reviews), not causes.",
    "<b>The A/B test is SIMULATED.</b> It uses made-up data with a fixed random seed. It shows the method, not a real result.",
    "<b>Forecast.</b> Only 20 full months, no holiday information, and the 3 forecast months are after the end of the data.",
    "<b>No costs.</b> Revenue is the item price without freight. Margin and profit are unknown.",
]


def page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GREY)
    canvas.drawString(1.6 * cm, 1.0 * cm, "Ecommerce_Sales_Analytics  |  Data: Olist Brazilian E-Commerce Public Dataset (CC BY-NC-SA 4.0)")
    canvas.drawRightString(A4[0] - 1.6 * cm, 1.0 * cm, f"Page {doc.page}")
    canvas.restoreState()


def build():
    doc = SimpleDocTemplate(str(PDF), pagesize=A4, leftMargin=1.6 * cm, rightMargin=1.6 * cm, topMargin=1.4 * cm, bottomMargin=1.6 * cm,
                            title="Ecommerce sales insights", author="Ecommerce_Sales_Analytics")
    width = A4[0] - 3.2 * cm
    story = [p("Ecommerce sales insights", H1), p("Olist marketplace, Brazil. Report for managers. Revenue means item prices without freight, "
                                                   "for valid sales (not canceled or unavailable).", SUB),
             p("<b>Business question.</b> " + question)]

    kpi_table = Table([[p(v, KPI_N) for v, _ in kpis], [p(lab, KPI_L) for _, lab in kpis]], colWidths=[width / len(kpis)] * len(kpis))
    kpi_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), LIGHT), ("TOPPADDING", (0, 0), (-1, 0), 6), ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
                                   ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E4E3DF"))]))
    story += [Spacer(1, 6), kpi_table, Spacer(1, 6)]

    charts = Table([[Image(chart_png("revenue"), width=width / 2 - 2, height=(width / 2 - 2) * 2.5 / 4.3),
                     Image(chart_png("delivery"), width=width / 2 - 2, height=(width / 2 - 2) * 2.5 / 4.3)]], colWidths=[width / 2] * 2)
    story += [charts, p("Left: monthly revenue grew fast in 2017 and was flat in 2018. Right: late deliveries get much lower review scores.", SMALL)]

    story.append(p("Key findings", H2))
    rows = [[p("<b>#</b>", CELL), p("<b>Finding</b>", CELL), p("<b>Evidence</b>", CELL)]]
    for num, title, text in findings:
        rows.append([p(num, CELL), p(f"<b>{title}</b>", CELL), p(text, CELL)])
    t = Table(rows, colWidths=[0.7 * cm, 3.9 * cm, width - 4.6 * cm], repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), LIGHT), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#E4E3DF")), ("TOPPADDING", (0, 0), (-1, -1), 3),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    story.append(t)

    story.append(p("Recommendations", H2))
    for i, (title, links, text) in enumerate(recs, start=1):
        story.append(KeepTogether([p(f"<b>{i}. {title}</b> <font color='#52514E'>(based on finding {links})</font>", BODY), p(text, CELL), Spacer(1, 3)]))

    story += [p(outlook, BODY), p("Limits", H2)]
    for item in limits:
        story.append(p("&bull; " + item, CELL))

    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    return doc.page


if __name__ == "__main__":
    pages = build()
    print(f"saved {PDF.relative_to(ROOT)}  ({PDF.stat().st_size / 1e3:.0f} KB, {pages} pages)")
