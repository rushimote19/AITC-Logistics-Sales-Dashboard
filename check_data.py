
import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1234",
    database="aitc_logistics"
)

cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM aitc_combined_data")
total_rows = cursor.fetchone()[0]

print("MySQL connection successful!")
print("Total AITC rows:", total_rows)

cursor.close()
conn.close()
