
import pandas as pd

file_path = r"C:\AITC_Automation\incoming\AITC_Combined_Data.csv"

df = pd.read_csv(file_path, encoding="utf-8-sig")

print("CSV file read successfully!")
print("Total rows:", len(df))
print("Total columns:", len(df.columns))
print("Column names:")
print(df.columns.tolist())

print("\nFirst 5 rows:")
print(df.head().to_string(index=False))
print("\nCSV sales total:", df["Sales_Amount"].sum())
print("CSV minimum sale:", df["Sales_Amount"].min())
print("CSV maximum sale:", df["Sales_Amount"].max())