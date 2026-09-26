import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path


# --------------------------------------------------
# 1. Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="EV Charging Monitoring Platform",
    page_icon="⚡",
    layout="wide"
)

st.title("EV Charging Monitoring Platform")
st.caption("Sub-Project 4 — Charging Monitoring & Visualization")


# --------------------------------------------------
# 2. File paths
# --------------------------------------------------

# dashboard.py is located at:
# ev-charging-platform/subprojects/sp4-monitoring-dashboard/dashboard.py

CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent.parent

FORECAST_FILE = (
    REPO_ROOT
    / "data"
    / "processed"
    / "sp1-demand-forecast-v1.csv"
)


# --------------------------------------------------
# 3. Load SP1 forecast data
# --------------------------------------------------

if not FORECAST_FILE.exists():
    st.error(f"Forecast file not found: {FORECAST_FILE}")
    st.stop()

forecast_data = pd.read_csv(FORECAST_FILE)


# --------------------------------------------------
# 4. Temporary EV monitoring data
# --------------------------------------------------
# This is temporary demo data.
# Later it can be replaced by real charging telemetry.

ev_data = pd.DataFrame({
    "EV_ID": [
        "EV01", "EV02", "EV03", "EV04", "EV05",
        "EV06", "EV07", "EV08", "EV09", "EV10"
    ],

    "SOC": [
        32, 67, 45, 81, 26,
        54, 72, 39, 61, 48
    ],

    "Status": [
        "Charging",
        "Waiting",
        "Charging",
        "Waiting",
        "Charging",
        "Charging",
        "Waiting",
        "Charging",
        "Waiting",
        "Charging"
    ],

    "Power_kW": [
        7.2, 0, 11, 0, 7.2,
        11, 0, 7.2, 0, 11
    ]
})


# --------------------------------------------------
# 5. Calculate key metrics
# --------------------------------------------------

total_evs = len(ev_data)

charging_evs = (
    ev_data["Status"] == "Charging"
).sum()

total_power = ev_data["Power_kW"].sum()

average_soc = ev_data["SOC"].mean()


# --------------------------------------------------
# 6. Display metrics
# --------------------------------------------------

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Total EVs",
    total_evs
)

col2.metric(
    "Charging EVs",
    charging_evs
)

col3.metric(
    "Total Charging Power",
    f"{total_power:.1f} kW"
)

col4.metric(
    "Average SOC",
    f"{average_soc:.1f}%"
)


# --------------------------------------------------
# 7. EV monitoring table
# --------------------------------------------------

st.subheader("EV Charging Status")

st.dataframe(
    ev_data,
    use_container_width=True
)


# --------------------------------------------------
# 8. SP1 Demand Forecast
# --------------------------------------------------

st.subheader("SP1 Demand Forecast")

st.caption(
    "Data source: data/processed/sp1-demand-forecast-v1.csv"
)

st.dataframe(
    forecast_data,
    use_container_width=True
)


# --------------------------------------------------
# 9. Show CSV column names
# --------------------------------------------------

st.write("Forecast CSV columns:")
st.write(forecast_data.columns.tolist())