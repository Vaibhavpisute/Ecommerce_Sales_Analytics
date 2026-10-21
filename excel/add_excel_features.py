"""Step 2 of the Excel report: add real Excel features with COM automation (pywin32).

Adds to excel/sales_report.xlsx: two Power Query queries (Q06 and Q15 CSV files), PivotTables, two slicers
(region, year) and PivotCharts. Excel must be installed. Run after excel/build_workbook.py:

    .venv\\Scripts\\python excel\\add_excel_features.py
"""
from pathlib import Path

import pythoncom
import win32com.client as win32

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "excel" / "sales_report.xlsx"
OUT = ROOT / "sql" / "outputs"

XL_DATABASE, XL_ROW, XL_COLUMN, XL_SUM, XL_DESC = 1, 1, 2, -4157, 2
XL_COLUMN_CLUSTERED, XL_LINE_MARKERS = 51, 65
BLUE_BGR = 42 + 120 * 256 + 214 * 65536     # #2a78d6 as an Excel color number

# The data folder is read from the named cell DataFolder (README sheet) INSIDE each query.
# A separate parameter query does not work here: Excel's privacy firewall blocks a query that reads
# another query and opens a file in the same step ("Formula.Firewall" error).
M_Q06 = """let
    Folder = Excel.CurrentWorkbook(){{[Name="DataFolder"]}}[Content]{{0}}[Column1],
    Source = Csv.Document(File.Contents(Text.TrimEnd(Folder, "\\") & "\\{file}"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {{{{"category_en", type text}}, {{"rank_in_category", Int64.Type}}, {{"product_id", type text}}, {{"orders", Int64.Type}}, {{"units", Int64.Type}}, {{"revenue", type number}}}}),
    Top3 = Table.SelectRows(Typed, each [rank_in_category] <= 3)
in
    Top3"""

M_Q15 = """let
    Folder = Excel.CurrentWorkbook(){{[Name="DataFolder"]}}[Content]{{0}}[Column1],
    Source = Csv.Document(File.Contents(Text.TrimEnd(Folder, "\\") & "\\{file}"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {{{{"level", type text}}, {{"region", type text}}, {{"state", type text}}, {{"payment_type", type text}}, {{"orders", Int64.Type}}, {{"revenue", type number}}, {{"avg_order_value", type number}}, {{"sd_order_value", type number}}}}),
    OnlyStates = Table.SelectRows(Typed, each [level] = "State")
in
    OnlyStates"""


def m_formula(template, file_name):
    # The templates use doubled braces for {{...}} lists; format() turns them into single braces
    return template.format(file=file_name)


def add_query(wb, name, formula, sheet_name):
    wb.Queries.Add(name, formula)
    ws = wb.Worksheets.Add(After=wb.Worksheets(wb.Worksheets.Count))
    ws.Name = sheet_name
    conn = f'OLEDB;Provider=Microsoft.Mashup.OleDb.1;Data Source=$Workbook$;Location={name};Extended Properties=""'
    # positional arguments: SourceType, Source, LinkSource, HasHeaders, Destination (keyword form fails in pywin32)
    lo = ws.ListObjects.Add(0, conn, False, 1, ws.Range("A1"))
    lo.Name = f"tbl_{name}"
    qt = lo.QueryTable
    qt.CommandType = 2        # xlCmdSql
    qt.CommandText = f"SELECT * FROM [{name}]"
    qt.RefreshStyle = 1
    qt.BackgroundQuery = False
    qt.Refresh(False)
    ws.Columns.AutoFit()
    print(f"  query {name}: {lo.ListRows.Count} rows loaded to sheet {sheet_name}")
    return ws


def main():
    xl = win32.DispatchEx("Excel.Application")
    xl.Visible = True
    xl.DisplayAlerts = False
    wb = xl.Workbooks.Open(str(XLSX))
    try:
        # ---------- Power Query ----------
        q06 = next(OUT.glob("q06_*.csv"))
        q15 = next(OUT.glob("q15_*.csv"))
        print("Power Query")
        add_query(wb, "q06_top3_products", m_formula(M_Q06, q06.name), "PQ_Top3_Products")
        add_query(wb, "q15_state_orders", m_formula(M_Q15, q15.name), "PQ_State_Orders")

        # ---------- PivotTables, slicers, PivotCharts ----------
        print("PivotTables")
        ws = wb.Worksheets.Add(After=wb.Worksheets("Segments"))
        ws.Name = "Pivot"
        ws.Range("A1").Value = "PivotTables with slicers (region and year slicers change all three PivotTables and both charts)"
        ws.Range("A1").Font.Bold = True
        ws.Range("A1").Font.Size = 14
        ws.Range("A2").Value = "Revenue = item price without freight, valid sales. Source: table tblItems on the Items sheet."

        cache = wb.PivotCaches().Create(SourceType=XL_DATABASE, SourceData="tblItems")

        def make_pivot(dest, name):
            return cache.CreatePivotTable(TableDestination=ws.Range(dest), TableName=name)

        def add_revenue(pt, field="price", caption="Revenue"):
            df = pt.AddDataField(pt.PivotFields(field), caption, XL_SUM)
            df.NumberFormat = "#,##0"

        # 1) revenue by region
        pt_region = make_pivot("A24", "ptRegion")
        pt_region.PivotFields("region").Orientation = XL_ROW
        add_revenue(pt_region)
        pt_region.PivotFields("region").AutoSort(XL_DESC, "Revenue")

        # 2) revenue by month
        pt_month = make_pivot("D24", "ptMonth")
        pt_month.PivotFields("month").Orientation = XL_ROW
        pt_month.PivotFields("month").NumberFormat = "yyyy-mm"
        add_revenue(pt_month)
        # only full months in the monthly view (2016 and 2018-09 have too few orders)
        pt_month.PivotFields("full_month").Orientation = 3          # xlPageField
        pt_month.PivotFields("full_month").CurrentPage = "Yes"

        # 3) revenue by category (rows) and state (columns)
        pt_cat = make_pivot("G24", "ptCategoryState")
        pt_cat.PivotFields("category").Orientation = XL_ROW
        pt_cat.PivotFields("state").Orientation = XL_COLUMN
        add_revenue(pt_cat)
        pt_cat.PivotFields("category").AutoSort(XL_DESC, "Revenue")

        # Slicers: region and year, connected to all three PivotTables
        slicer_defs = [("region", "slRegion", "Region", 5), ("year", "slYear", "Year", 160)]
        for field, name, caption, left in slicer_defs:
            sc = wb.SlicerCaches.Add2(pt_cat, field)
            sl = sc.Slicers.Add(ws, pythoncom.Missing, name, caption)
            # position and size are set as properties (the arguments of Add were not applied reliably)
            sl.Name, sl.Caption = name, caption
            sl.Top, sl.Left, sl.Width, sl.Height = 40, left, 150, 220
            sc.PivotTables.AddPivotTable(pt_region)
            sc.PivotTables.AddPivotTable(pt_month)
        print("  3 PivotTables and 2 slicers created")

        # PivotCharts
        def pivot_chart(pt, kind, left, title, x_title, y_title, name):
            shape = ws.Shapes.AddChart2(-1, kind, left, 30, 400, 235)
            shape.Name = name
            chart = shape.Chart
            chart.SetSourceData(pt.TableRange1)
            chart.HasTitle = True
            chart.ChartTitle.Text = title
            chart.HasLegend = False
            chart.Axes(1).HasTitle = True
            chart.Axes(1).AxisTitle.Text = x_title
            chart.Axes(2).HasTitle = True
            chart.Axes(2).AxisTitle.Text = y_title
            try:
                chart.ShowAllFieldButtons = False
            except Exception:
                pass
            return chart

        ws.Columns("A:B").ColumnWidth = 14
        ws.Columns("D:E").ColumnWidth = 12
        pivot_chart(pt_region, XL_COLUMN_CLUSTERED, 335, "Revenue by region", "Region", "Revenue (BRL)", "chRegion")
        pivot_chart(pt_month, XL_LINE_MARKERS, 745, "Revenue by month", "Month", "Revenue (BRL)", "chMonth")
        print("  2 PivotCharts created")

        # ---------- Native charts on the KPIs sheet (data = the monthly formulas) ----------
        print("KPI charts")
        kpi = wb.Worksheets("KPIs")
        n_months = 20
        first_row, last_row = 12, 11 + n_months
        kpi_charts = [("Revenue per month", "Revenue (BRL)", "C", XL_COLUMN_CLUSTERED, "J3"),
                      ("Orders per month", "Orders", "B", XL_LINE_MARKERS, "J20"),
                      ("Average order value (AOV) per month", "AOV (BRL)", "D", XL_LINE_MARKERS, "J37")]
        for title, y_title, col, kind, anchor in kpi_charts:
            at = kpi.Range(anchor)
            shape = kpi.Shapes.AddChart2(-1, kind, at.Left, at.Top, 470, 235)
            shape.Name = "kpi_" + title.split()[0].lower()
            chart = shape.Chart
            while chart.SeriesCollection().Count:
                chart.SeriesCollection(1).Delete()
            series = chart.SeriesCollection().NewSeries()
            series.Name = title
            series.Values = kpi.Range(f"{col}{first_row}:{col}{last_row}")
            series.XValues = kpi.Range(f"A{first_row}:A{last_row}")
            if kind == XL_COLUMN_CLUSTERED:
                series.Format.Fill.ForeColor.RGB = BLUE_BGR
            else:
                series.Format.Line.ForeColor.RGB = BLUE_BGR
                series.MarkerBackgroundColor = BLUE_BGR
                series.MarkerForegroundColor = BLUE_BGR
            chart.HasTitle = True
            chart.ChartTitle.Text = title
            chart.HasLegend = False
            chart.Axes(1).CategoryType = 2           # text axis, so months are not treated as a date scale
            chart.Axes(1).TickLabels.NumberFormat = "yyyy-mm"
            chart.Axes(1).HasTitle = True
            chart.Axes(1).AxisTitle.Text = "Month"
            chart.Axes(2).HasTitle = True
            chart.Axes(2).AxisTitle.Text = y_title
            chart.Axes(2).TickLabels.NumberFormat = "#,##0"
        print("  3 native charts created on KPIs")

        # sheet order (Add(After=...) is not applied reliably through pywin32, so move the sheets)
        for name in reversed(["README", "KPIs", "Segments", "Pivot", "PQ_Top3_Products", "PQ_State_Orders", "Data", "Items"]):
            wb.Worksheets(name).Move(Before=wb.Worksheets(1))
        wb.Worksheets("README").Activate()
        wb.Save()
        print("saved")
    finally:
        wb.Close(SaveChanges=False)
        xl.Quit()


if __name__ == "__main__":
    main()
