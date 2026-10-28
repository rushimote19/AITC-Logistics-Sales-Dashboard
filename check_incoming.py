
from pathlib import Path
from datetime import datetime
import pandas as pd

INCOMING = Path(r"C:\AITC_Automation\incoming")
LOG_FILE = Path(r"C:\AITC_Automation\logs\automation.log")

REQUIRED_COLUMNS = [
    "Date", "Customer", "Voucher_No", "GSTIN_UIN",
    "Order_Details", "Payment_Terms", "Destination",
    "Destination_Standardized", "Sales_Amount",
    "Financial_Year", "Month"
]

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(message)

def check_incoming_files():
    files = list(INCOMING.glob("*.csv"))

    if not files:
        log("No new CSV files found.")
        return

    for file in files:
        try:
            df = pd.read_csv(file, encoding="utf-8-sig")

            missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
            if missing:
                log(f"INVALID: {file.name}; missing columns: {missing}")
                continue

            log(
                f"VALID: {file.name}; rows={len(df)}; "
                f"sales_total={df['Sales_Amount'].sum():.2f}"
            )

        except Exception as e:
            log(f"ERROR: {file.name}; {e}")

if __name__ == "__main__":
    check_incoming_files()
