
from pathlib import Path
from datetime import datetime
import pandas as pd
import mysql.connector
import shutil

# File locations
INCOMING = Path(r"C:\AITC_Automation\incoming")
ARCHIVE = Path(r"C:\AITC_Automation\archive")
LOG_FILE = Path(r"C:\AITC_Automation\logs\automation.log")

# SAFETY: Keep True until dry-run testing is verified
DRY_RUN = True

REQUIRED_COLUMNS = [
    "Date",
    "Customer",
    "Voucher_No",
    "GSTIN_UIN",
    "Order_Details",
    "Payment_Terms",
    "Destination",
    "Destination_Standardized",
    "Sales_Amount",
    "Financial_Year",
    "Month"
]


def log(message):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

    print(message)


def archive_file(file):
    ARCHIVE.mkdir(parents=True, exist_ok=True)

    destination = ARCHIVE / file.name

    if destination.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = ARCHIVE / (
            f"{file.stem}_{timestamp}{file.suffix}"
        )

    shutil.move(str(file), str(destination))
    log(f"ARCHIVED {file.name} -> {destination.name}")


def read_sales_file(file):
    extension = file.suffix.lower()

    if extension == ".csv":
        return pd.read_csv(file, encoding="utf-8-sig")

    if extension == ".xlsx":
        return pd.read_excel(file, engine="openpyxl")

    raise ValueError(f"Unsupported file format: {extension}")


def validate_sales_data(df, file):
    missing = [
        col for col in REQUIRED_COLUMNS
        if col not in df.columns
    ]

    if missing:
        raise ValueError(f"Missing columns: {missing}")

    if df.empty:
        raise ValueError("File contains no data rows")

    # Validate voucher numbers
    if df["Voucher_No"].isna().any():
        raise ValueError("Blank voucher number found")

    df["Voucher_No"] = df["Voucher_No"].astype(str).str.strip()

    if df["Voucher_No"].eq("").any():
        raise ValueError("Empty voucher number found")

    if df["Voucher_No"].duplicated().any():
        raise ValueError("Duplicate vouchers found inside file")

    # Validate customer names
    if df["Customer"].isna().any():
        raise ValueError("Blank customer name found")

    if df["Customer"].astype(str).str.strip().eq("").any():
        raise ValueError("Empty customer name found")

    # Validate dates
    df["Date"] = pd.to_datetime(
        df["Date"], errors="raise"
    )

    if df["Date"].isna().any():
        raise ValueError("Blank date found")

    df["Date"] = df["Date"].dt.date

    # Validate sales amounts
    df["Sales_Amount"] = pd.to_numeric(
        df["Sales_Amount"], errors="raise"
    )

    if df["Sales_Amount"].isna().any():
        raise ValueError("Blank sales amount found")

    if (df["Sales_Amount"] < 0).any():
        raise ValueError("Negative sales amount found")

    return df


def load_new_sales():
    INCOMING.mkdir(parents=True, exist_ok=True)

    files = sorted(
        file for file in (
            list(INCOMING.glob("*.csv"))
            + list(INCOMING.glob("*.xlsx"))
        )
        if not file.name.startswith("~$")
    )

    if not files:
        log("No new CSV or Excel files found.")
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
                log(f"READING {file.name}")

                df = read_sales_file(file)
                df = validate_sales_data(df, file)

                cursor.execute(
                    "SELECT Voucher_No FROM aitc_combined_data"
                )

                existing = {
                    str(row[0]).strip()
                    for row in cursor.fetchall()
                    if row[0] is not None
                }

                new_count = int(
                    (~df["Voucher_No"].isin(existing)).sum()
                )

                existing_count = len(df) - new_count

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
                    `Destination_Standardized` =
                        VALUES(`Destination_Standardized`),
                    `Sales_Amount` = VALUES(`Sales_Amount`),
                    `Financial_Year` = VALUES(`Financial_Year`),
                    `Month` = VALUES(`Month`)
                """

                columns = REQUIRED_COLUMNS
                values = []

                for row in df[columns].itertuples(
                    index=False, name=None
                ):
                    values.append(tuple(
                        None if pd.isna(value) else value
                        for value in row
                    ))

                file_total = float(df["Sales_Amount"].sum())

                if DRY_RUN:
                    log(
                        f"DRY RUN PASSED: {file.name}; "
                        f"rows={len(values)}; "
                        f"new vouchers={new_count}; "
                        f"existing vouchers={existing_count}; "
                        f"file sales total={file_total:.2f}; "
                        "NO DATA INSERTED OR UPDATED; "
                        "FILE NOT ARCHIVED"
                    )

                else:
                    cursor.executemany(sql, values)
                    conn.commit()

                    log(
                        f"SUCCESS {file.name}: "
                        f"processed rows={len(values)}; "
                        f"new vouchers={new_count}; "
                        f"existing vouchers={existing_count}; "
                        f"file sales total={file_total:.2f}"
                    )

                    archive_file(file)

            except Exception as e:
                if conn:
                    conn.rollback()

                log(f"REJECTED/ERROR {file.name}: {e}")

    except Exception as e:
        log(f"DATABASE CONNECTION ERROR: {e}")

    finally:
        if cursor:
            cursor.close()

        if conn and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    load_new_sales()
