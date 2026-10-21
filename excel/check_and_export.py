"""Step 3 of the Excel report: reopen excel/sales_report.xlsx in Excel, recalculate, check it, and export PNG files.

Checks: no error values on any sheet (#REF!, #NAME?, #VALUE!, #DIV/0!, #N/A ...), the KPI sheet equals the SQL results (Q2, Q3),
the PivotTable grand total equals the total revenue, and the number of PivotTables, slicers, queries and charts.
Exports charts and ranges to screenshots/excel_*.png. Writes excel/check_report.md.

    .venv\\Scripts\\python excel\\check_and_export.py
"""
import shutil
import tempfile
from pathlib import Path

import pandas as pd
import win32com.client as win32

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "excel" / "sales_report.xlsx"
OUT = ROOT / "sql" / "outputs"
SHOTS = ROOT / "screenshots"
REPORT = ROOT / "excel" / "check_report.md"

XL_CELLTYPE_FORMULAS, XL_CELLTYPE_CONSTANTS, XL_ERRORS = -4123, 2, 16
lines, failures, failed_images = [], [], []


def log(text):
    print(text)
    lines.append(text)


def count_errors(ws):
    total = 0
    for cell_type in (XL_CELLTYPE_FORMULAS, XL_CELLTYPE_CONSTANTS):
        try:
            total += ws.UsedRange.SpecialCells(cell_type, XL_ERRORS).Count
        except Exception:      # Excel raises an error when no cell matches: that means no errors
            pass
    return total


def export_chart(chart_object, name):
    path = SHOTS / name
    try:
        chart_object.Chart.Export(str(path))
        log(f"- exported {name}")
    except Exception as e:
        failed_images.append(name)
        log(f"- FAILED to export {name}: {e}")


def export_range(ws, address, name):
    path = SHOTS / name
    try:
        ws.Activate()
        rng = ws.Range(address)
        rng.CopyPicture(1, 2)
        temp = ws.ChartObjects().Add(0, 0, rng.Width, rng.Height)
        temp.Activate()
        temp.Chart.Paste()
        temp.Chart.Export(str(path))
        temp.Delete()
        log(f"- exported {name}")
    except Exception as e:
        failed_images.append(name)
        log(f"- FAILED to export {name}: {e}")


def refresh_query_sheet(wb, sheet):
    wb.Worksheets(sheet).ListObjects(1).QueryTable.Refresh(False)
    return wb.Worksheets(sheet).ListObjects(1).ListRows.Count


def check_data_folder(wb):
    """Point the named cell DataFolder to a folder with changed copies of Q06 and Q15, refresh, and check the row counts."""
    cell = wb.Names("DataFolder").RefersToRange
    original = cell.Value
    q06_file = next(OUT.glob("q06_*.csv"))
    q15_file = next(OUT.glob("q15_*.csv"))
    log(f"- named cell DataFolder = {cell.Parent.Name}!{cell.Address}, value: {original}")
    tmp = Path(tempfile.mkdtemp(prefix="datafolder_test_"))
    try:
        d06 = pd.read_csv(q06_file)
        d06[d06.rank_in_category > 1].to_csv(tmp / q06_file.name, index=False)        # copy without the rank 1 rows
        d15 = pd.read_csv(q15_file)
        drop = d15[d15.level == "State"].index[:10]
        d15.drop(index=drop).to_csv(tmp / q15_file.name, index=False)                  # copy without 10 state rows
        expected = {"PQ_Top3_Products": int(((d06.rank_in_category > 1) & (d06.rank_in_category <= 3)).sum()),
                    "PQ_State_Orders": int((d15.level == "State").sum()) - 10}
        base = {"PQ_Top3_Products": int((d06.rank_in_category <= 3).sum()), "PQ_State_Orders": int((d15.level == "State").sum())}
        try:
            cell.Value = str(tmp)
            for sheet in expected:
                got = refresh_query_sheet(wb, sheet)
                ok = got == expected[sheet]
                log(f"- folder changed to a test folder: {sheet} now has {got} rows (expected {expected[sheet]}) -> {'OK' if ok else 'MISMATCH'}")
                if not ok:
                    failures.append(f"DataFolder parameter does not change {sheet}")
            cell.Value = str(tmp / "does_not_exist")
            try:
                refresh_query_sheet(wb, "PQ_State_Orders")
                log("- wrong folder: refresh did NOT fail -> MISMATCH")
                failures.append("wrong DataFolder did not raise an error")
            except Exception:
                log("- wrong folder: refresh fails with an error, as expected -> OK")
        finally:
            cell.Value = original
            for sheet in expected:
                got = refresh_query_sheet(wb, sheet)
                ok = got == base[sheet]
                log(f"- folder restored: {sheet} has {got} rows (expected {base[sheet]}) -> {'OK' if ok else 'MISMATCH'}")
                if not ok:
                    failures.append(f"{sheet} not restored after the DataFolder test")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    SHOTS.mkdir(exist_ok=True)
    xl = win32.DispatchEx("Excel.Application")
    xl.Visible = True
    xl.DisplayAlerts = False
    wb = xl.Workbooks.Open(str(XLSX))
    try:
        xl.CalculateFull()
        log("# Excel check report\n")
        log("## 1. Error values on every sheet")
        for ws in wb.Worksheets:
            n = count_errors(ws)
            log(f"- {ws.Name}: {n} error cells")
            if n:
                failures.append(f"{ws.Name} has {n} error cells")

        log("\n## 2. KPI sheet vs SQL (Q2 and Q3)")
        ws = wb.Worksheets("KPIs")
        q2 = pd.read_csv(next(OUT.glob("q02_*.csv"))).query("in_analysis_period").reset_index(drop=True)
        q3 = pd.read_csv(next(OUT.glob("q03_*.csv")))
        n = len(q2)
        rows = ws.Range(ws.Cells(12, 1), ws.Cells(11 + n, 5)).Value
        xdf = pd.DataFrame(rows, columns=["month", "orders", "revenue", "aov", "mom"])
        diffs = {
            "orders": float((xdf.orders - q2.orders).abs().max()),
            "revenue": float((xdf.revenue - q2.revenue).abs().max()),
            "aov": float((xdf.aov - q2.aov).abs().max()),
            "mom growth (percentage points)": float((pd.to_numeric(xdf.mom, errors="coerce") * 100 - q3.mom_growth_pct).abs().max()),
        }
        for k, v in diffs.items():
            ok = v < 0.011
            log(f"- {k}: largest difference to SQL = {v:.4f} -> {'OK' if ok else 'MISMATCH'}")
            if not ok:
                failures.append(f"KPI {k} differs from SQL by {v}")
        total_rev = ws.Range("B4").Value
        total_orders = ws.Range("B5").Value
        sql_rev = pd.read_csv(next(OUT.glob("q02_*.csv"))).revenue.sum()
        sql_orders = pd.read_csv(next(OUT.glob("q02_*.csv"))).orders.sum()
        log(f"- total revenue: Excel {total_rev:,.2f} vs SQL {sql_rev:,.2f}; total orders: Excel {total_orders:,.0f} vs SQL {sql_orders:,.0f}")
        if abs(total_rev - sql_rev) > 0.05 or total_orders != sql_orders:
            failures.append("KPI totals differ from SQL")

        log("\n## 3. PivotTables, slicers, queries, charts")
        pv = wb.Worksheets("Pivot")
        pivots = {pt.Name: pt for pt in pv.PivotTables()}
        region_total = pivots["ptRegion"].GetPivotData("Revenue").Value
        cat_total = pivots["ptCategoryState"].GetPivotData("Revenue").Value
        log(f"- PivotTables: {len(pivots)} ({', '.join(pivots)})")
        log(f"- PivotTable grand total revenue (by region): {region_total:,.2f}; (by category and state): {cat_total:,.2f}; SQL: {sql_rev:,.2f}")
        if abs(region_total - sql_rev) > 0.05 or abs(cat_total - sql_rev) > 0.05:
            failures.append("PivotTable total differs from SQL")
        log(f"- Slicers: {wb.SlicerCaches.Count} ({', '.join(sc.Name for sc in wb.SlicerCaches)})")
        log(f"- Power Query queries: {wb.Queries.Count} ({', '.join(q.Name for q in wb.Queries)})")
        log(f"- Native charts on KPIs: {ws.ChartObjects().Count}; PivotCharts on Pivot: {pv.ChartObjects().Count}")
        log(f"- Rows loaded by Power Query: {wb.Worksheets('PQ_Top3_Products').ListObjects(1).ListRows.Count} (Q06, top 3 per category), "
            f"{wb.Worksheets('PQ_State_Orders').ListObjects(1).ListRows.Count} (Q15, states)")

        log("\n## 4. Power Query parameter: named cell DataFolder")
        check_data_folder(wb)

        log("\n## 5. Exported images")
        export_chart(ws.ChartObjects(1), "excel_02_kpi_revenue_chart.png")
        export_chart(ws.ChartObjects(2), "excel_03_kpi_orders_chart.png")
        export_chart(ws.ChartObjects(3), "excel_04_kpi_aov_chart.png")
        export_range(ws, "A1:H32", "excel_01_kpi_table.png")
        export_range(wb.Worksheets("Segments"), "A1:H13", "excel_05_segments.png")
        export_chart(pv.ChartObjects("chRegion"), "excel_07_pivot_chart_region.png")
        export_chart(pv.ChartObjects("chMonth"), "excel_08_pivot_chart_month.png")
        export_range(pv, "A1:W45", "excel_06_pivot_slicers.png")

        wb.Worksheets("README").Activate()
        wb.Save()
        log("\nWorkbook saved after recalculation.")
    finally:
        wb.Close(SaveChanges=False)
        xl.Quit()

    log("\n## Result")
    if failures:
        log("**PROBLEMS:** " + "; ".join(failures))
    else:
        log("All checks passed: no error cells, KPIs and PivotTables equal the SQL results.")
    if failed_images:
        log("Images not exported (take these screenshots by hand): " + ", ".join(failed_images))
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
