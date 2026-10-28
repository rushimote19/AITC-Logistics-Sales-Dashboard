import pandas as pd
from pathlib import Path

folder = Path(r"C:\AITC_Automation\incoming")
folder.mkdir(parents=True, exist_ok=True)

file = folder / "AITC_DRY_RUN_TEST.xlsx"

columns = [
    "Date", "Customer", "Voucher_No", "GSTIN_UIN",
    "Order_Details", "Payment_Terms", "Destination",
    "Destination_Standardized", "Sales_Amount",
    "Financial_Year", "Month"
]

row = {
    "Date": "2026-10-15",
    "Customer": "AITC DRY RUN TEST ONLY",
    "Voucher_No": "AITC_DRYRUN_ONLY_20261015",
    "GSTIN_UIN": "",
    "Order_Details": "TEST ONLY - DO NOT USE FOR SALES",
    "Payment_Terms": "Test",
    "Destination": "Test Destination",
    "Destination_Standardized": "Test Destination",
    "Sales_Amount": 123.45,
    "Financial_Year": "2026-2027",
    "Month": "October"
}

pd.DataFrame([row], columns=columns).to_excel(
    file, index=False, engine="openpyxl"
)

print("Test Excel created:", file)
print("Rows:", 1)
print("Test sales amount: 123.45")
print("No database changes made by this script.")