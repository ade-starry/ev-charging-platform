import streamlit as st
import pandas as pd
import plotly.express as px


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

ev_data = pd.read_csv("data/ev_data.csv")


# --------------------------------------------------
# 3. Calculate key metrics
# --------------------------------------------------

total_evs = len(ev_data)

charging_evs = (
    ev_data["Status"] == "Charging"
).sum()

total_power = ev_data["Power_kW"].sum()

average_soc = ev_data["SOC"].mean()


# --------------------------------------------------
# 4. Display metrics
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
# 5. EV monitoring table
# --------------------------------------------------

st.subheader("EV Charging Status")

st.dataframe(ev_data)


# --------------------------------------------------
# 6. 24-hour charging load data
# --------------------------------------------------

load_data = pd.read_csv("data/load_data.csv")


# --------------------------------------------------
# 7. Plot charging load curve
# --------------------------------------------------

st.subheader("24-Hour Charging Load")

fig = px.line(
    load_data,
    x="Hour",
    y="Load_kW",
    markers=True,
    title="EV Charging Station Load"
)

fig.update_layout(
    xaxis_title="Hour",
    yaxis_title="Charging Power (kW)"
)

st.plotly_chart(fig)