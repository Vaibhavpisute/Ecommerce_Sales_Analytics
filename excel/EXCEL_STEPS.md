# Excel report: how it is built and what to check

`excel/sales_report.xlsx` is built **automatically** in 3 steps. Desktop Excel (Microsoft 365) must be installed
and no other Excel window should be busy. Run from the project root, in this order:

```
.venv\Scripts\python excel\build_workbook.py        # data sheets, KPI formulas, XLOOKUP, conditional formatting (openpyxl)
.venv\Scripts\python excel\add_excel_features.py    # Power Query, PivotTables, slicers, charts (Excel COM)
.venv\Scripts\python excel\check_and_export.py      # reopen, recalculate, check errors and numbers, export PNG files
```

The check step writes `excel/check_report.md`. It reopens the saved file in Excel and checks that: there are no error cells
on any sheet, the KPI sheet equals SQL queries Q2 and Q3, the PivotTable totals equal the total revenue from SQL, and the
`DataFolder` parameter really controls the Power Query queries.

## What is in the workbook

| Sheet | Content |
|---|---|
| README | Purpose, definitions, notes, and the named cell `DataFolder` (the parameter of the Power Query queries) |
| KPIs | Headline KPIs and monthly table with real formulas (`SUMIFS`, `COUNTIFS`, `AVERAGEIFS`, `IFERROR`), conditional formatting (growth up/down, low review scores) and 3 native charts |
| Segments | RFM segment table from Q12 with `XLOOKUP` to a description table, plus a list of a random sample of 500 customers (seed 42) |
| Pivot | 3 PivotTables (by region, by month, by category and state), 2 slicers (region, year) that control all of them, 2 PivotCharts |
| PQ_Top3_Products | Power Query: reads the Q06 CSV from the folder in the named cell `DataFolder`, sets column types, keeps the top 3 products per category |
| PQ_State_Orders | Power Query: reads the Q15 CSV from the folder in the named cell `DataFolder`, sets column types, keeps the rows at state level |
| Data | One row per valid order (98,199 rows, all data, no sampling) |
| Items | One row per item sold in a valid order (112,101 rows, all data, no sampling) |

## Things Excel automation could not do, or that you should know

Nothing is required by hand. Please check these points when you open the file:

1. **Power Query data folder (the parameter `DataFolder`).** The two Power Query queries no longer contain a fixed path.
   They read the folder of the SQL result files from a **named cell** called `DataFolder`. It is the yellow cell at the bottom of
   the **README** sheet (today `README!$A$24`). You can also find it with the Name Box next to the formula bar, or in
   **Formulas > Name Manager**. When the file is built, its value is the `sql\outputs` folder of this project on the building computer.
   - **If you move the project, or open the file on another computer:** type the new folder in the yellow cell
     (for example `C:\Users\me\Ecommerce_Sales_Analytics\sql\outputs`), then click **Data > Refresh All**.
     Nothing else has to be edited. A backslash at the end of the folder is allowed.
   - **How it works:** the first step of each query is
     `Folder = Excel.CurrentWorkbook(){[Name="DataFolder"]}[Content]{0}[Column1]`. The next step opens
     `Folder & "\q06_...csv"` (or `q15_...csv`).
   - **If the cell is wrong:** Refresh shows an error like "The system cannot find the path specified". Fix the cell and refresh again.
   - **Why the step is inside each query, not in a separate parameter query:** Excel's privacy firewall refuses a query that reads
     another query and opens a file (error `Formula.Firewall`: "references other queries or steps, so it may not directly access a
     data source"). A separate parameter query was tried first and failed.
   - **Tested:** `check_and_export.py` points the cell at a test folder that has changed copies of the files and refreshes (the row counts
     change as expected). It then points the cell at a folder that does not exist (the refresh fails). Finally it restores the
     original value and refreshes again (the original row counts come back).
2. **Number format on screen.** Numbers use the regional setting of Windows. On a computer with Indian regional settings you see
   `1,20,098.27`, on others `120,098.27`. The values are the same.
3. **Slicers.** Region and year slicers filter the three PivotTables and both PivotCharts. The "Revenue by month" PivotTable also has a
   fixed filter `full_month = Yes` (months 2017-01 to 2018-08). The other two PivotTables use all months.
4. **Screenshots.** All 8 images in `screenshots/` (`excel_01_...` to `excel_08_...`) were exported automatically. If you want a different
   look, take your own screenshot of the sheet and save it with the same file name.
5. **Do not edit the Data and Items sheets by hand** (they are Excel tables, `tblData` and `tblItems`; formulas and PivotTables depend on them).
   To change the data, run the three steps again.
