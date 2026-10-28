
from pathlib import Path
from datetime import datetime
import streamlit as st
import mysql.connector

BASE = Path(r"C:\AITC_Automation")
LOG_FILE = BASE / "logs" / "automation.log"
INCOMING = BASE / "incoming"
ARCHIVE = BASE / "archive"
PROCESSED = BASE / "processed"

st.set_page_config(
    page_title="AITC Logistics Automation",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
    .stApp {
        background-color: #f4f7fb;
    }

    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #dce5f0;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 3px 10px rgba(20, 45, 80, 0.06);
    }

    [data-testid="stMetricLabel"] {
        color: #52647a;
        font-size: 14px;
    }

    [data-testid="stMetricValue"] {
        color: #12345a;
        font-weight: 700;
    }

    h1 {
        color: #12345a;
        font-weight: 800;
    }

    h2, h3 {
        color: #234b75;
    }

    div.stButton > button {
        background-color: #155eef;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 8px 18px;
        font-weight: 600;
    }

    div.stButton > button:hover {
        background-color: #1249bd;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

st.title("AITC Logistics")
st.subheader("Automation Monitoring Dashboard")
st.caption("CSV Processing • Data Validation • MySQL • Sales Monitoring")

if st.button("🔄 Refresh Dashboard"):
    st.rerun()

# Read automation log
if LOG_FILE.exists():
    log_lines = LOG_FILE.read_text(
        encoding="utf-8", errors="replace"
    ).splitlines()
else:
    log_lines = []

latest_log = log_lines[-1] if log_lines else "No logs available"

def count_files(folder):
    return len(list(folder.glob("*"))) if folder.exists() else 0

incoming_count = count_files(INCOMING)
archive_count = count_files(ARCHIVE)
processed_count = count_files(PROCESSED)

errors = [x for x in log_lines if "ERROR" in x.upper()]
rejected = [x for x in log_lines if "REJECTED" in x.upper()]
skipped = [x for x in log_lines if "SKIPPED" in x.upper()]
dry_runs = [x for x in log_lines if "DRY RUN" in x.upper()]
successes = [x for x in log_lines if "SUCCESS" in x.upper()]

st.markdown("### Automation Status")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Incoming Files", incoming_count)
c2.metric("Archived Files", archive_count)
c3.metric("Rejected Events", len(rejected))
c4.metric("Logged Errors", len(errors))

st.info(f"Latest log entry: {latest_log}")

st.markdown("### Processing Summary")
a, b, c = st.columns(3)
a.metric("Dry-run Events", len(dry_runs))
b.metric("Duplicate/No-new-data Skips", len(skipped))
c.metric("Successful Loads Logged", len(successes))

st.markdown("### MySQL Sales Summary")
st.caption("Connect to view current database figures.")

with st.form("mysql_connection"):
    db_user = st.text_input("MySQL username", value="root")
    db_password = st.text_input(
        "MySQL password", type="password"
    )
    connect = st.form_submit_button("Connect to MySQL")

if connect:
    if not db_password:
        st.warning("Enter your MySQL password.")
    else:
        try:
            conn = mysql.connector.connect(
                host="localhost",
                user=db_user,
                password=db_password,
                database="aitc_logistics",
                connection_timeout=5
            )
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    COUNT(*) AS total_rows,
                    COUNT(DISTINCT Voucher_No) AS unique_vouchers,
                    COUNT(DISTINCT Customer) AS customers,
                    ROUND(SUM(Sales_Amount), 2) AS total_sales
                FROM aitc_combined_data
            """)
            result = cursor.fetchone()

            st.session_state["db_summary"] = result
            st.session_state["db_connected"] = True

            cursor.close()
            conn.close()
            st.success("Connected to MySQL successfully.")

        except Exception as exc:
            st.session_state["db_connected"] = False
            st.error(f"MySQL connection failed: {exc}")

if st.session_state.get("db_connected"):
    result = st.session_state.get("db_summary")
    if result:
        total_rows, vouchers, customers, sales = result
        x1, x2, x3, x4 = st.columns(4)
        x1.metric("Database Rows", f"{total_rows:,}")
        x2.metric("Unique Vouchers", f"{vouchers:,}")
        x3.metric("Customers", f"{customers:,}")
        x4.metric(
            "Total Sales",
            f"₹{sales:,.2f}" if sales is not None else "₹0.00"
        )

st.markdown("### Recent Automation Logs")
if log_lines:
    st.code("\n".join(log_lines[-20:]), language="text")
else:
    st.warning("No automation log file found yet.")

with st.expander("Rejected files and errors"):
    st.markdown("**Rejected events**")
    st.code("\n".join(rejected[-10:]) or "None logged")
    st.markdown("**Error events**")
    st.code("\n".join(errors[-10:]) or "None logged")

st.caption(
    "Note: Log counts are historical event counts, not necessarily "
    "unique files. Database figures show current stored data. "
    "A dry run does not insert or update records."
)
