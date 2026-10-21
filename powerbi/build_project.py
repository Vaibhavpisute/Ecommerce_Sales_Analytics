"""Generate the Power BI Project (PBIP): TMDL semantic model + PBIR report with 3 pages.

Output (in powerbi/):
  EcommerceSales.pbip
  EcommerceSales.SemanticModel/   definition.pbism + definition/ (TMDL: model, tables, relationships, expressions)
  EcommerceSales.Report/          definition.pbir + definition/ (PBIR: report, pages, visuals) + StaticResources/

The data comes from the CSV files made by powerbi/export_model_data.py (powerbi/data/).
Run from the project root:  .venv\\Scripts\\python powerbi\\build_project.py
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PBI = ROOT / "powerbi"
NAME = "EcommerceSales"
MODEL = PBI / f"{NAME}.SemanticModel"
REPORT = PBI / f"{NAME}.Report"
BASE_THEME_NAME = "CY26SU10"
BASE_THEME_SRC = (Path(r"C:\Program Files\WindowsApps\Microsoft.MicrosoftPowerBIDesktop_2.159.883.0_x64__8wekyb3d8bbwe")
                  / "bin" / "WebView2Resources" / "minerva" / "sharedresources" / "BaseThemes" / f"{BASE_THEME_NAME}.json")

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item"
T = "\t"

# =====================================================================================================
# 1. SEMANTIC MODEL (TMDL)
# =====================================================================================================
M_TYPES = {"int64": "Int64.Type", "double": "type number", "string": "type text", "dateTime": "type date"}

# column: (name, dataType, formatString or None, options)
TABLES = {
    "dim_date": {
        "csv": "dim_date.csv", "dataCategory": "Time",
        "cols": [("date", "dateTime", "yyyy-mm-dd", {"key": True}), ("year", "int64", "0", {}), ("quarter", "int64", "0", {}),
                 ("month", "int64", "0", {}), ("month_name", "string", None, {"sortBy": "month"}), ("year_month", "string", None, {}),
                 ("month_start", "dateTime", "yyyy-mm", {}), ("day_of_week", "int64", "0", {}),
                 ("day_name", "string", None, {"sortBy": "day_of_week"}), ("is_weekend", "string", None, {}),
                 ("analysis_flag", "int64", "0", {"hidden": True}), ("period_type", "string", None, {})],
    },
    "dim_state": {
        "csv": "dim_state.csv",
        "cols": [("state", "string", None, {}), ("state_name", "string", None, {"category": "StateOrProvince"}),
                 ("region", "string", None, {}), ("country", "string", None, {"category": "Country"})],
    },
    "dim_customer": {
        "csv": "dim_customer.csv",
        "cols": [("customer_key", "int64", "0", {"hidden": True}), ("state", "string", None, {"hidden": True}),
                 ("first_order_month", "dateTime", "yyyy-mm", {}), ("order_count", "int64", "0", {}),
                 ("revenue", "double", "#,0.00", {}), ("recency_days", "int64", "0", {}), ("r_score", "int64", "0", {}),
                 ("f_score", "int64", "0", {}), ("m_score", "int64", "0", {}), ("rfm_score", "string", None, {}),
                 ("segment", "string", None, {"sortBy": "segment_order"}), ("segment_order", "int64", "0", {"hidden": True})],
    },
    "dim_product": {
        "csv": "dim_product.csv",
        "cols": [("product_key", "int64", "0", {"hidden": True}), ("product_id", "string", None, {}),
                 ("category", "string", None, {}), ("weight_g", "double", "#,0", {})],
    },
    "fact_orders": {
        "csv": "fact_orders.csv",
        "cols": [("order_key", "int64", "0", {"hidden": True}), ("customer_key", "int64", "0", {"hidden": True}),
                 ("purchase_date", "dateTime", "yyyy-mm-dd", {}), ("purchase_hour", "int64", "0", {}),
                 ("order_status", "string", None, {}), ("payment_type", "string", None, {}),
                 ("items_value", "double", "#,0.00", {}), ("freight_value", "double", "#,0.00", {}),
                 ("review_score", "int64", "0", {}), ("delivery_days", "double", "0.0", {}), ("delay_days", "double", "0.0", {}),
                 ("late_flag", "int64", "0", {}), ("low_review_flag", "int64", "0", {}),
                 ("delay_bucket", "string", None, {"sortBy": "delay_bucket_order"}),
                 ("delay_bucket_order", "int64", "0", {"hidden": True})],
    },
    "fact_order_items": {
        "csv": "fact_order_items.csv",
        "cols": [("order_key", "int64", "0", {"hidden": True}), ("product_key", "int64", "0", {"hidden": True}),
                 ("price", "double", "#,0.00", {}), ("freight_value", "double", "#,0.00", {})],
    },
    "cohort_retention": {
        "csv": "cohort_retention.csv",
        "cols": [("cohort_month", "string", None, {}), ("month_index", "int64", "0", {}), ("cohort_size", "int64", "#,0", {}),
                 ("active_customers", "int64", "#,0", {}), ("retention_pct", "double", "0.00", {})],
    },
    "top_customers": {
        "csv": "top_customers.csv",
        "cols": [("customer_key", "int64", "0", {"hidden": True}), ("customer_unique_id", "string", None, {}),
                 ("revenue_rank", "int64", "0", {}), ("orders", "int64", "0", {}), ("clv_revenue", "double", "#,0.00", {}),
                 ("avg_order_value", "double", "#,0.00", {}), ("first_order_date", "dateTime", "yyyy-mm-dd", {}),
                 ("last_order_date", "dateTime", "yyyy-mm-dd", {}), ("active_days", "int64", "0", {}),
                 ("cumulative_revenue_share_pct", "double", "0.00", {})],
    },
    "low_performers": {
        "csv": "low_performers.csv",
        "cols": [("product_key", "int64", "0", {"hidden": True}), ("reviewed_orders", "int64", "0", {}),
                 ("avg_rating", "double", "0.00", {}), ("low_score_pct", "double", "0.0", {}),
                 ("overall_avg_rating", "double", "0.00", {})],
    },
}

# measure: (name, DAX, formatString, displayFolder, description)
MEASURES = {
    "fact_order_items": [
        ("Total Revenue", "SUM(fact_order_items[price])", "#,0.00", "Sales",
         "Sum of item prices (without freight) of valid sales."),
        ("Total Orders", "DISTINCTCOUNT(fact_order_items[order_key])", "#,0", "Sales", "Number of valid orders that have items."),
        ("AOV", "DIVIDE([Total Revenue], [Total Orders])", "#,0.00", "Sales", "Average order value = revenue / orders."),
        ("Freight Value", "SUM(fact_order_items[freight_value])", "#,0.00", "Sales", "Sum of freight."),
        ("Units Sold", "COUNTROWS(fact_order_items)", "#,0", "Sales", "Number of items sold."),
        ("Revenue Previous Month", "CALCULATE([Total Revenue], DATEADD(dim_date[date], -1, MONTH))", "#,0.00", "Growth",
         "Revenue of the month before."),
        ("MoM Growth %", """VAR prevRevenue = [Revenue Previous Month]
VAR bothMonthsComplete =
    MAX(dim_date[analysis_flag]) = 1
        && CALCULATE(MAX(dim_date[analysis_flag]), DATEADD(dim_date[date], -1, MONTH)) = 1
RETURN
    IF(
        HASONEVALUE(dim_date[year_month]) && bothMonthsComplete,
        DIVIDE([Total Revenue] - prevRevenue, prevRevenue)
    )""", "0.0%", "Growth",
         "Month-over-month revenue growth. Empty unless a single month is in scope and both months are full months (same rule as SQL Q3)."),
        ("MoM Growth % (last full month)", """VAR lastMonth =
    MAXX(
        FILTER(
            VALUES(dim_date[month_start]),
            [Total Revenue] > 0 && CALCULATE(MAX(dim_date[analysis_flag])) = 1
        ),
        dim_date[month_start]
    )
RETURN
    CALCULATE([MoM Growth %], dim_date[month_start] = lastMonth)""", "0.0%", "Growth",
         "MoM growth of the last full month in the selected dates (for the KPI card)."),
        ("Revenue YTD", "TOTALYTD([Total Revenue], dim_date[date])", "#,0", "Growth", "Revenue from 1 January of the year to the date."),
        ("Revenue Share %", "DIVIDE([Total Revenue], CALCULATE([Total Revenue], ALLSELECTED(dim_product[category])))", "0.0%", "Products",
         "Share of the selected categories' revenue."),
        ("Category Rank", "RANKX(ALLSELECTED(dim_product[category]), [Total Revenue], , DESC, Dense)", "0", "Products",
         "Rank of the category by revenue."),
        ("Revenue (Top 10 Categories)", "IF([Category Rank] <= 10, [Total Revenue])", "#,0", "Products",
         "Revenue, only for the 10 best categories (other categories are empty and hidden in charts)."),
        ("State Rank", "RANKX(ALLSELECTED(dim_state[state_name]), [Total Revenue], , DESC, Dense)", "0", "Geography",
         "Rank of the customer state by revenue."),
        ("Revenue (Top 10 States)", "IF([State Rank] <= 10, [Total Revenue])", "#,0", "Geography",
         "Revenue, only for the 10 best states (other states are empty and hidden in charts)."),
        ("Cumulative Revenue % (Top 20)", """VAR currentRevenue = [Total Revenue]
VAR allCategories = ALLSELECTED(dim_product[category])
VAR cumulative = SUMX(FILTER(allCategories, [Total Revenue] >= currentRevenue), [Total Revenue])
VAR total = SUMX(allCategories, [Total Revenue])
RETURN
    IF([Category Rank] <= 20, DIVIDE(cumulative, total))""", "0.0%", "Products",
         "Pareto: running share of revenue when categories are sorted from high to low (first 20 categories)."),
    ],
    "fact_orders": [
        ("Average Review Score", "AVERAGE(fact_orders[review_score])", "0.00", "Quality", "Average review score (1 to 5)."),
        ("Late Delivery Rate", "AVERAGE(fact_orders[late_flag])", "0.0%", "Quality",
         "Share of delivered orders that arrived after the estimated date."),
        ("Average Delivery Days", "AVERAGE(fact_orders[delivery_days])", "0.0", "Quality", "Days from purchase to delivery."),
        ("Avg Review by Delay", "CALCULATE(AVERAGE(fact_orders[review_score]), fact_orders[delay_bucket_order] <= 5)", "0.00", "Quality",
         "Average review score of delivered orders (empty for orders that were not delivered)."),
        ("Low Review Share by Delay", "CALCULATE(AVERAGE(fact_orders[low_review_flag]), fact_orders[delay_bucket_order] <= 5)", "0.0%", "Quality",
         "Share of reviews with score 1 or 2, delivered orders only."),
        ("Active Customers", "DISTINCTCOUNT(fact_orders[customer_key])", "#,0", "Customers",
         "Customers (customer_unique_id) with at least one valid order in scope."),
        ("New Customers", """VAR firstMonth = MIN(dim_date[month_start])
VAR lastMonth = MAX(dim_date[month_start])
RETURN
    CALCULATE(
        DISTINCTCOUNT(fact_orders[customer_key]),
        FILTER(
            ALL(dim_customer[first_order_month]),
            dim_customer[first_order_month] >= firstMonth && dim_customer[first_order_month] <= lastMonth
        )
    )""", "#,0", "Customers", "Customers whose first order month is inside the selected months (same rule as SQL Q9)."),
        ("Repeat Customers", "[Active Customers] - [New Customers]", "#,0", "Customers",
         "Active customers who first bought in an earlier month (same rule as SQL Q9)."),
        ("Returning Customer % (period)", "DIVIDE([Repeat Customers], [Active Customers])", "0.0%", "Customers",
         "Share of active customers who first bought earlier (SQL Q9 repeat_customer_pct)."),
        ("Customers with 2+ Orders", "CALCULATE(DISTINCTCOUNT(fact_orders[customer_key]), dim_customer[order_count] >= 2)", "#,0", "Customers",
         "Customers with 2 or more valid orders in the whole data (SQL Q10 repeat_customers when nothing is filtered)."),
        ("One-time Customers", "CALCULATE(DISTINCTCOUNT(fact_orders[customer_key]), dim_customer[order_count] = 1)", "#,0", "Customers",
         "Customers with exactly one valid order (SQL Q10 customers_with_1_order when nothing is filtered)."),
        ("Repeat Customer %", """DIVIDE(
    CALCULATE(DISTINCTCOUNT(fact_orders[customer_key]), dim_customer[order_count] >= 2),
    [Active Customers]
)""", "0.0%", "Customers",
         "Share of customers with 2 or more valid orders in the whole data (SQL Q10 repeat_purchase_rate_pct when nothing is filtered)."),
    ],
    "cohort_retention": [
        ("Cohort Retention %", "DIVIDE(SUM(cohort_retention[active_customers]), SUM(cohort_retention[cohort_size]))", "0.00%", "Customers",
         "Customers of the cohort who ordered again in the month, as a share of the cohort (SQL Q11)."),
    ],
}

RELATIONSHIPS = [
    ("fact_orders", "purchase_date", "dim_date", "date"),
    ("fact_orders", "customer_key", "dim_customer", "customer_key"),
    ("dim_customer", "state", "dim_state", "state"),
    ("fact_order_items", "order_key", "fact_orders", "order_key"),
    ("fact_order_items", "product_key", "dim_product", "product_key"),
    ("top_customers", "customer_key", "dim_customer", "customer_key"),
    ("low_performers", "product_key", "dim_product", "product_key"),
]


def q(name):
    """Quote a TMDL object name when needed."""
    return name if name.replace("_", "").isalnum() else "'" + name.replace("'", "''") + "'"


def indent(text, level):
    return "\n".join((T * level + line) if line.strip() else "" for line in text.split("\n"))


def table_tmdl(name, spec):
    out = [f"table {name}"]
    if spec.get("dataCategory"):
        out.append(f"{T}dataCategory: {spec['dataCategory']}")
    out.append("")
    for mname, dax, fmt, folder, desc in MEASURES.get(name, []):
        for line in desc.split("\n"):
            out.append(f"{T}/// {line}")
        if "\n" in dax:
            out.append(f"{T}measure {q(mname)} =")
            out.append(indent(dax, 3))
        else:
            out.append(f"{T}measure {q(mname)} = {dax}")
        out.append(f"{T * 2}formatString: {fmt}")
        out.append(f"{T * 2}displayFolder: {folder}")
        out.append("")
    for cname, dtype, fmt, opts in spec["cols"]:
        out.append(f"{T}column {q(cname)}")
        out.append(f"{T * 2}dataType: {dtype}")
        if fmt:
            out.append(f"{T * 2}formatString: {fmt}")
        if opts.get("hidden"):
            out.append(f"{T * 2}isHidden")
        if opts.get("key"):
            out.append(f"{T * 2}isKey")
        if opts.get("category"):
            out.append(f"{T * 2}dataCategory: {opts['category']}")
        if opts.get("sortBy"):
            out.append(f"{T * 2}sortByColumn: {q(opts['sortBy'])}")
        out.append(f"{T * 2}summarizeBy: none")
        out.append(f"{T * 2}sourceColumn: {cname}")
        out.append("")
    types = ", ".join(f'{{"{c[0]}", {M_TYPES[c[1]]}}}' for c in spec["cols"])
    m = (f'let\n'
         f'    Source = Csv.Document(File.Contents(Text.TrimEnd(DataFolder, "\\") & "\\{spec["csv"]}"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),\n'
         f'    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),\n'
         f'    ChangedTypes = Table.TransformColumnTypes(PromotedHeaders, {{{types}}}, "en-US")\n'
         f'in\n'
         f'    ChangedTypes')
    out.append(f"{T}partition {q(name)} = m")
    out.append(f"{T * 2}mode: import")
    out.append(f"{T * 2}source =")
    out.append(indent(m, 3))
    out.append("")
    return "\n".join(out)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def build_model():
    if MODEL.exists():
        shutil.rmtree(MODEL)
    write(MODEL / "definition.pbism", json.dumps({"$schema": f"{SCHEMA}/semanticModel/definitionProperties/1.0.0/schema.json",
                                                   "version": "4.0", "settings": {}}, indent=2) + "\n")
    d = MODEL / "definition"
    write(d / "database.tmdl", f"database\n{T}compatibilityLevel: 1600\n")
    refs = "\n".join(f"ref table {n}" for n in TABLES)
    write(d / "model.tmdl",
          f"model Model\n{T}culture: en-US\n{T}defaultPowerBIDataSourceVersion: powerBI_V3\n{T}discourageImplicitMeasures\n"
          f"{T}sourceQueryCulture: en-US\n{T}dataAccessOptions\n{T * 2}legacyRedirects\n{T * 2}returnErrorValuesAsNull\n\n{refs}\n")
    data_dir = str(PBI / "data")
    write(d / "expressions.tmdl",
          f'expression DataFolder = "{data_dir}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n'
          f"{T}annotation PBI_ResultType = Text\n")
    rel = []
    for f_table, f_col, t_table, t_col in RELATIONSHIPS:
        rel.append(f"relationship {f_table}_{f_col}_to_{t_table}_{t_col}\n{T}fromColumn: {f_table}.{f_col}\n{T}toColumn: {t_table}.{t_col}\n")
    write(d / "relationships.tmdl", "\n".join(rel))
    for name, spec in TABLES.items():
        write(d / "tables" / f"{name}.tmdl", table_tmdl(name, spec))


# =====================================================================================================
# 2. REPORT (PBIR)
# =====================================================================================================
def lit(value):
    return {"expr": {"Literal": {"Value": value}}}


def field(kind, table, prop):
    return {kind: {"Expression": {"SourceRef": {"Entity": table}}, "Property": prop}}


def proj(kind, table, prop, active=False):
    p = {"field": field(kind, table, prop), "queryRef": f"{table}.{prop}", "nativeQueryRef": prop}
    if active:
        p["active"] = True
    return p


def full_months_filter(name):
    """Visual-level filter: dim_date[analysis_flag] = 1, so monthly charts show full months only (2017-01 to 2018-08)."""
    column = {"Column": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": "analysis_flag"}}
    return {"filters": [{
        "name": f"full_months_{name}"[:50],
        "field": field("Column", "dim_date", "analysis_flag"),
        "type": "Categorical",
        "filter": {"Version": 2, "From": [{"Name": "d", "Entity": "dim_date", "Type": 0}],
                   "Where": [{"Condition": {"In": {"Expressions": [column], "Values": [[{"Literal": {"Value": "1L"}}]]}}}]},
    }]}


def container(name, x, y, w, h, visual, z=0, filter_config=None):
    c = {"$schema": f"{SCHEMA}/report/definition/visualContainer/2.13.0/schema.json", "name": name,
         "position": {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z},
         "visual": visual}
    if filter_config:
        c["filterConfig"] = filter_config
    return c


def title_obj(text):
    return {"title": [{"properties": {"show": lit("true"), "text": lit("'" + text.replace("'", "''") + "'")}}]}


def card(name, x, y, w, h, table, measure, z):
    v = {"visualType": "card", "query": {"queryState": {"Values": {"projections": [proj("Measure", table, measure)]}}},
         "drillFilterOtherVisuals": True}
    return container(name, x, y, w, h, v, z)


def slicer(name, x, y, w, h, table, column, mode, group, z, title):
    v = {"visualType": "slicer",
         "query": {"queryState": {"Values": {"projections": [proj("Column", table, column, active=True)]}}},
         "objects": {"data": [{"properties": {"mode": lit(f"'{mode}'")}}],
                     "header": [{"properties": {"show": lit("false")}}]},
         "visualContainerObjects": title_obj(title),
         "syncGroup": {"groupName": group, "fieldChanges": True, "filterChanges": True},
         "drillFilterOtherVisuals": True}
    return container(name, x, y, w, h, v, z)


def chart(name, x, y, w, h, vtype, title, category, values, z, sort_measure=None, series=None, full_months=False,
          sort_direction="Descending"):
    """category = (table, column); values = [(kind, table, prop), ...]; full_months = visual filter on full months only"""
    state = {"Category": {"projections": [proj("Column", category[0], category[1], active=True)]},
             "Y": {"projections": [proj(k, t, p) for k, t, p in values]}}
    if series:
        state["Series"] = {"projections": [proj("Column", series[0], series[1], active=True)]}
    query = {"queryState": state}
    if sort_measure:
        query["sortDefinition"] = {"sort": [{"field": field("Measure", sort_measure[0], sort_measure[1]), "direction": sort_direction}],
                                   "isDefaultSort": False}
    v = {"visualType": vtype, "query": query, "visualContainerObjects": title_obj(title), "drillFilterOtherVisuals": True}
    return container(name, x, y, w, h, v, z, filter_config=full_months_filter(name) if full_months else None)


def matrix(name, x, y, w, h, title, row, column, value, z):
    v = {"visualType": "pivotTable",
         "query": {"queryState": {"Rows": {"projections": [proj("Column", row[0], row[1], active=True)]},
                                  "Columns": {"projections": [proj("Column", column[0], column[1], active=True)]},
                                  "Values": {"projections": [proj("Measure", value[0], value[1])]}}},
         "visualContainerObjects": title_obj(title), "drillFilterOtherVisuals": True}
    return container(name, x, y, w, h, v, z)


def table(name, x, y, w, h, title, columns, z, sort=None):
    """columns = [(kind, table, prop), ...]; sort = (kind, table, prop, direction)"""
    query = {"queryState": {"Values": {"projections": [proj(k, t, p) for k, t, p in columns]}}}
    if sort:
        query["sortDefinition"] = {"sort": [{"field": field(sort[0], sort[1], sort[2]), "direction": sort[3]}], "isDefaultSort": False}
    v = {"visualType": "tableEx", "query": query, "visualContainerObjects": title_obj(title), "drillFilterOtherVisuals": True}
    return container(name, x, y, w, h, v, z)


def filled_map(name, x, y, w, h, title, z):
    # Known limit (see POWERBI_STEPS.md): in Power BI Desktop 2.159 this map highlights the customer states but does not
    # shade them by revenue. Two role names / a colour rule were tried and did not change it. The revenue by state is
    # shown as a bar chart (page 1). To shade the map, drag Total Revenue into "Color saturation" by hand.
    v = {"visualType": "filledMap",
         "query": {"queryState": {"Category": {"projections": [proj("Column", "dim_state", "state_name", active=True)]},
                                  "Y": {"projections": [proj("Measure", "fact_order_items", "Total Revenue")]}}},
         "visualContainerObjects": title_obj(title), "drillFilterOtherVisuals": True}
    return container(name, x, y, w, h, v, z)


def slicer_bar(prefix, first_z=100):
    """Date, category and state slicers: the same 3 slicers on every page (synchronised)."""
    return [
        slicer(f"{prefix}_slicer_date", 20, 6, 380, 72, "dim_date", "date", "Between", "sync_date", first_z, "Date range"),
        slicer(f"{prefix}_slicer_category", 420, 6, 410, 72, "dim_product", "category", "Dropdown", "sync_category", first_z + 1,
               "Product category"),
        slicer(f"{prefix}_slicer_state", 850, 6, 410, 72, "dim_state", "state_name", "Dropdown", "sync_state", first_z + 2,
               "Customer state"),
    ]


def page_sales():
    p = "s1"
    vs = slicer_bar(p)
    cards = [("Total Revenue", "Total Revenue"), ("Total Orders", "Total Orders"), ("Average Order Value", "AOV"),
             ("MoM Growth", "MoM Growth % (last full month)"), ("Revenue YTD", "Revenue YTD")]
    for i, (label, m) in enumerate(cards):
        vs.append(card(f"{p}_card_{i + 1}", 20 + i * 248, 84, 240, 86, "fact_order_items", m, i + 1))
    vs.append(chart(f"{p}_line_revenue", 20, 182, 760, 250, "lineChart", "Revenue by month (full months)", ("dim_date", "year_month"),
                    [("Measure", "fact_order_items", "Total Revenue")], 10, full_months=True))
    vs.append(chart(f"{p}_col_mom", 800, 182, 460, 250, "clusteredColumnChart", "MoM revenue growth by month",
                    ("dim_date", "year_month"), [("Measure", "fact_order_items", "MoM Growth %")], 11, full_months=True))
    vs.append(chart(f"{p}_col_orders", 20, 444, 410, 266, "clusteredColumnChart", "Orders by month (full months)",
                    ("dim_date", "year_month"), [("Measure", "fact_order_items", "Total Orders")], 12, full_months=True))
    vs.append(chart(f"{p}_line_aov", 445, 444, 410, 266, "lineChart", "Average order value by month (full months)",
                    ("dim_date", "year_month"), [("Measure", "fact_order_items", "AOV")], 13, full_months=True))
    vs.append(chart(f"{p}_bar_state", 870, 444, 390, 266, "clusteredBarChart", "Top 10 states by revenue", ("dim_state", "state_name"),
                    [("Measure", "fact_order_items", "Revenue (Top 10 States)")], 14,
                    sort_measure=("fact_order_items", "Revenue (Top 10 States)")))
    return "SalesOverview", "Sales Overview", vs


def page_customers():
    p = "c1"
    vs = slicer_bar(p)
    cards = [("Active Customers", "fact_orders", "Active Customers"), ("2+ orders", "fact_orders", "Customers with 2+ Orders"),
             ("One order", "fact_orders", "One-time Customers"), ("Repeat Customer %", "fact_orders", "Repeat Customer %")]
    for i, (label, t, m) in enumerate(cards):
        vs.append(card(f"{p}_card_{i + 1}", 20 + i * 310, 84, 300, 86, t, m, i + 1))
    vs.append(chart(f"{p}_col_new_repeat", 20, 182, 620, 250, "columnChart", "New and repeat customers by month (full months)",
                    ("dim_date", "year_month"), [("Measure", "fact_orders", "New Customers"), ("Measure", "fact_orders", "Repeat Customers")], 10,
                    full_months=True))
    vs.append(chart(f"{p}_line_returning", 660, 182, 600, 250, "lineChart", "Returning customers as a share of the month's customers",
                    ("dim_date", "year_month"), [("Measure", "fact_orders", "Returning Customer % (period)")], 11, full_months=True))
    vs.append(matrix(f"{p}_matrix_cohort", 20, 444, 470, 266, "Cohort retention (share of the cohort ordering again)",
                     ("cohort_retention", "cohort_month"), ("cohort_retention", "month_index"), ("cohort_retention", "Cohort Retention %"), 12))
    vs.append(chart(f"{p}_bar_segments", 505, 444, 360, 266, "clusteredBarChart", "Customers by RFM segment", ("dim_customer", "segment"),
                    [("Measure", "fact_orders", "Active Customers")], 13))
    vs.append(table(f"{p}_table_top", 880, 444, 380, 266, "Top customers by revenue (top 5%, from Q13)",
                    [("Column", "top_customers", "revenue_rank"), ("Column", "top_customers", "orders"),
                     ("Column", "top_customers", "clv_revenue")], 14, sort=("Column", "top_customers", "revenue_rank", "Ascending")))
    return "Customers", "Customers", vs


def page_products():
    p = "p1"
    vs = slicer_bar(p)
    vs.append(chart(f"{p}_bar_top_categories", 20, 84, 410, 298, "clusteredBarChart", "Top 10 categories by revenue",
                    ("dim_product", "category"), [("Measure", "fact_order_items", "Revenue (Top 10 Categories)")], 10,
                    sort_measure=("fact_order_items", "Revenue (Top 10 Categories)")))
    vs.append(chart(f"{p}_line_pareto", 445, 84, 410, 298, "lineChart", "Pareto: running share of revenue (first 20 categories)",
                    ("dim_product", "category"), [("Measure", "fact_order_items", "Cumulative Revenue % (Top 20)")], 11,
                    sort_measure=("fact_order_items", "Cumulative Revenue % (Top 20)"), sort_direction="Ascending"))
    vs.append(filled_map(f"{p}_map_state", 870, 84, 390, 298, "Customer states (map)", 12))
    vs.append(chart(f"{p}_col_review_delay", 20, 394, 410, 316, "clusteredColumnChart", "Average review score by delivery delay",
                    ("fact_orders", "delay_bucket"), [("Measure", "fact_orders", "Avg Review by Delay")], 13))
    vs.append(chart(f"{p}_col_lowshare_delay", 445, 394, 410, 316, "clusteredColumnChart", "Share of low reviews (1 or 2) by delivery delay",
                    ("fact_orders", "delay_bucket"), [("Measure", "fact_orders", "Low Review Share by Delay")], 14))
    vs.append(table(f"{p}_table_low", 870, 394, 390, 316, "Low performers: many orders, low rating (Q8)",
                    [("Column", "dim_product", "category"), ("Column", "low_performers", "reviewed_orders"),
                     ("Column", "low_performers", "avg_rating"), ("Column", "low_performers", "low_score_pct")], 15,
                    sort=("Column", "low_performers", "avg_rating", "Ascending")))
    return "ProductsDelivery", "Products & Delivery", vs


def build_report():
    if REPORT.exists():
        shutil.rmtree(REPORT)
    write(REPORT / "definition.pbir",
          json.dumps({"$schema": f"{SCHEMA}/report/definitionProperties/2.0.0/schema.json", "version": "4.0",
                      "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}}}, indent=2) + "\n")
    d = REPORT / "definition"
    write(d / "version.json", json.dumps({"$schema": f"{SCHEMA}/report/definition/versionMetadata/1.0.0/schema.json", "version": "2.0.0"}, indent=2) + "\n")
    report = {
        "$schema": f"{SCHEMA}/report/definition/report/3.3.0/schema.json",
        "themeCollection": {"baseTheme": {"name": BASE_THEME_NAME, "reportVersionAtImport": {"visual": "2.13.0", "page": "2.1.0", "report": "3.3.0"},
                                          "type": "SharedResources"}},
        "resourcePackages": [{"name": "SharedResources", "type": "SharedResources",
                              "items": [{"name": BASE_THEME_NAME, "path": f"BaseThemes/{BASE_THEME_NAME}.json", "type": "BaseTheme"}]}],
    }
    write(d / "report.json", json.dumps(report, indent=2) + "\n")
    if BASE_THEME_SRC.exists():
        dest = REPORT / "StaticResources" / "SharedResources" / "BaseThemes" / f"{BASE_THEME_NAME}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(BASE_THEME_SRC, dest)
    else:
        print("WARNING: base theme file not found; Power BI Desktop may add it when you save.")

    pages = [page_sales(), page_customers(), page_products()]
    for page_name, display, visuals in pages:
        write(d / "pages" / page_name / "page.json",
              json.dumps({"$schema": f"{SCHEMA}/report/definition/page/2.1.0/schema.json", "name": page_name, "displayName": display,
                          "displayOption": "FitToPage", "height": 720, "width": 1280}, indent=2) + "\n")
        for v in visuals:
            write(d / "pages" / page_name / "visuals" / v["name"] / "visual.json", json.dumps(v, indent=2) + "\n")
    write(d / "pages" / "pages.json",
          json.dumps({"$schema": f"{SCHEMA}/report/definition/pagesMetadata/1.1.0/schema.json",
                      "pageOrder": [p[0] for p in pages], "activePageName": pages[0][0]}, indent=2) + "\n")


def build_pbip():
    write(PBI / f"{NAME}.pbip",
          json.dumps({"$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json", "version": "1.0",
                      "artifacts": [{"report": {"path": f"{NAME}.Report"}}], "settings": {"enableAutoRecovery": True}}, indent=2) + "\n")
    write(PBI / ".gitignore", "**/.pbi/localSettings.json\n**/.pbi/cache.abf\n")


REQUIRED = ["Total Revenue", "Total Orders", "AOV", "MoM Growth %", "Repeat Customer %", "Revenue YTD", "Average Review Score"]
SQL_CHECK = {
    "Total Revenue": "13,494,400.74 with no filters (Q2 sum of all months; Q15 'All orders').",
    "Total Orders": "98,199 with no filters (Q2 sum of all months).",
    "AOV": "137.42 with no filters (Q15 'All orders').",
    "MoM Growth %": "SQL Q3 mom_growth_pct for each month from 2017-02 to 2018-08 (for example 2018-08: -3.32%; the KPI card shows -3.3%).",
    "Repeat Customer %": "3.04% with no filters (SQL Q10: 2,887 of 94,983 customers).",
    "Revenue YTD": "At 2018-08-31 it equals the sum of Q2 revenue from 2018-01 to 2018-08.",
    "Average Review Score": "About 4.12 with no filters (4.1164 in the export control numbers).",
}


def write_dax_doc():
    lines = ["# DAX measures", "",
             "All measures are stored in the semantic model (`powerbi/EcommerceSales.SemanticModel`). This file is written by "
             "`powerbi/build_project.py` from the same definitions, so it always matches the model.", "",
             "Revenue means the item price without freight, for valid sales only (not canceled or unavailable).", "",
             "## The 7 required measures", "",
             "| Measure | What it does | Expected value (from the SQL results, to compare in Power BI) |", "|---|---|---|"]
    by_name = {m[0]: (t, m) for t, ms in MEASURES.items() for m in ms}
    for name in REQUIRED:
        t, m = by_name[name]
        lines.append(f"| **{name}** | {m[4]} | {SQL_CHECK[name]} |")
    lines += ["", "## All measures", ""]
    for t, ms in MEASURES.items():
        lines += [f"### Table `{t}`", ""]
        for name, dax, fmt, folder, desc in ms:
            lines += [f"**{name}** ({folder}, format `{fmt}`): {desc}", "", "```dax", f"{name} =", dax, "```", ""]
    lines += ["## Model notes", "",
              "- `dim_date` is the date table (marked as date table, complete years 2016 to 2018). `analysis_flag` = 1 for the full months 2017-01 to 2018-08.",
              "- Filters flow like this: `dim_date`, `dim_state` -> `dim_customer` -> `fact_orders` -> `fact_order_items`, and `dim_product` -> `fact_order_items`.",
              "- The category slicer filters revenue and orders (`fact_order_items`). It does not filter review, delivery and customer measures (`fact_orders`).",
              "- `cohort_retention` has no relationships. The date, category and state slicers do not change the cohort matrix (it is all-time, from Q11).",
              "- Monthly charts have a visual-level filter `analysis_flag = 1`, so the incomplete months (2016, 2018-09) are not drawn.", ""]
    write(PBI / "DAX_MEASURES.md", "\n".join(lines))


if __name__ == "__main__":
    build_model()
    build_report()
    build_pbip()
    write_dax_doc()
    n_vis = sum(1 for _ in (REPORT / "definition" / "pages").rglob("visual.json"))
    print(f"Project written to {PBI}: {len(TABLES)} tables, {sum(len(v) for v in MEASURES.values())} measures, "
          f"{len(RELATIONSHIPS)} relationships, 3 pages, {n_vis} visuals")
