
from pathlib import Path
from datetime import datetime
import pandas as pd
import mysql.connector
import shutil

INCOMING = Path(r"C:\AITC_Automation\incoming")
ARCHIVE = Path(r"C:\AITC_Automation\archive")
LOG_FILE = Path(r"C:\AITC_Automation\logs\automation.log")
DRY_RUN = True
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
    
def archive_file(file):
    ARCHIVE.mkdir(parents=True, exist_ok=True)

    destination = ARCHIVE / file.name

    if destination.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = ARCHIVE / f"{file.stem}_{timestamp}{file.suffix}"

    shutil.move(str(file), str(destination))
    log(f"ARCHIVED {file.name} -> {destination.name}")


def load_new_sales():
    files = list(INCOMING.glob("*.csv"))

    if not files:
        log("No new CSV files found.")
        return

    conn = None
    cursor = None

    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="1234",
            database="aitc_logistics"
        )
        cursor = conn.cursor()

        for file in files:
            try:
                df = pd.read_csv(file, encoding="utf-8-sig")

                missing = [
                    col for col in REQUIRED_COLUMNS
                    if col not in df.columns
                ]
                if missing:
                    log(f"REJECTED {file.name}: missing columns {missing}")
                    continue

                if df["Voucher_No"].isna().any():
                    log(f"REJECTED {file.name}: blank voucher number")
                    continue

                df["Voucher_No"] = df["Voucher_No"].astype(str).str.strip()

                if (df["Voucher_No"] == "").any():
                    log(f"REJECTED {file.name}: blank voucher number")
                    continue

                if df["Voucher_No"].duplicated().any():
                    log(f"REJECTED {file.name}: duplicate vouchers inside CSV")
                    continue

                
                # Validate required business fields
                if df["Customer"].isna().any():
                    log(f"REJECTED {file.name}: blank customer names")
                    continue

                if df["Customer"].astype(str).str.strip().eq("").any():
                    log(f"REJECTED {file.name}: empty customer names")
                    continue

                # Validate dates
                df["Date"] = pd.to_datetime(
                    df["Date"], errors="raise"
                ).dt.date

                # Validate sales amounts
                df["Sales_Amount"] = pd.to_numeric(
                    df["Sales_Amount"], errors="raise"
                )

                if df["Sales_Amount"].isna().any():
                    log(f"REJECTED {file.name}: blank sales amounts")
                    continue

                if (df["Sales_Amount"] < 0).any():
                    log(f"REJECTED {file.name}: negative sales amounts")
                    continue


                cursor.execute(
                    "SELECT Voucher_No FROM aitc_combined_data"
                )
                existing = {row[0] for row in cursor.fetchall()}

                new_df = df[
                    ~df["Voucher_No"].isin(existing)
                ].copy()

                
                # Identify new and existing vouchers
                new_count = int(
                    (~df["Voucher_No"].isin(existing)).sum()
                )
                existing_count = len(df) - new_count

                columns = REQUIRED_COLUMNS

                sql = """
                    INSERT INTO aitc_combined_data
                    (`Date`, `Customer`, `Voucher_No`, `GSTIN_UIN`,
                     `Order_Details`, `Payment_Terms`, `Destination`,
                     `Destination_Standardized`, `Sales_Amount`,
                     `Financial_Year`, `Month`)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    `Date` = VALUES(`Date`),
                    `Customer` = VALUES(`Customer`),
                    `GSTIN_UIN` = VALUES(`GSTIN_UIN`),
                    `Order_Details` = VALUES(`Order_Details`),
                    `Payment_Terms` = VALUES(`Payment_Terms`),
                    `Destination` = VALUES(`Destination`),
                    `Destination_Standardized` = VALUES(`Destination_Standardized`),
                    `Sales_Amount` = VALUES(`Sales_Amount`),
                    `Financial_Year` = VALUES(`Financial_Year`),
                    `Month` = VALUES(`Month`)
                """

                values = []
                for row in df[columns].itertuples(
                    index=False, name=None
                ):
                    values.append(tuple(
                        None if pd.isna(value) else value
                        for value in row
                    ))

                if DRY_RUN:
                    log(
                        f"DRY RUN: {file.name}; "
                        f"total rows={len(values)}; "
                        f"new vouchers={new_count}; "
                        f"existing vouchers={existing_count}; "
                        f"file sales total={df['Sales_Amount'].sum():.2f}; "
                        "NO DATA INSERTED OR UPDATED"
                    )
                else:
                    cursor.executemany(sql, values)
                    conn.commit()

                    log(
                        f"SUCCESS {file.name}: "
                        f"processed rows={len(values)}; "
                        f"new vouchers={new_count}; "
                        f"existing vouchers checked={existing_count}; "
                        f"file sales total={df['Sales_Amount'].sum():.2f}"
                    )
                    archive_file(file)


            except Exception as e:
                if conn:
                    conn.rollback()
                log(f"ERROR {file.name}: {e}")

    except Exception as e:
        log(f"DATABASE CONNECTION ERROR: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    load_new_sales()
