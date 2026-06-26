"""
app.py — Sahar-Connect emergency dashboard (Streamlit).

A lightweight kiosk/operator UI that talks to the edge API and proves the whole
loop end-to-end:
  1. shows the edge node is online,
  2. plots responders + active alerts on a map of Al Qua'a,
  3. lets a farmer raise an alert and instantly shows the nearest responder.

Run it (with the edge API also running):
    streamlit run src/dashboard/app.py
"""

import os

import pandas as pd
import requests
import streamlit as st

EDGE_API_URL = os.getenv("EDGE_API_URL", "http://localhost:8000")

st.set_page_config(page_title="Sahar-Connect", page_icon="🛰️", layout="wide")

# --- Kiosk accessibility styling -------------------------------------------
# High contrast, large fonts, and big touch targets so the dashboard is usable
# by rural residents on a sun-glared kiosk screen or a phone in the field.
st.markdown(
    """
    <style>
        /* Larger base typography for readability */
        html { font-size: 18px; }
        h1 { font-size: 2.4rem !important; }
        label, .stMarkdown p { font-size: 1.15rem !important; }

        /* Massive, high-contrast emergency button */
        .stButton > button {
            width: 100%;
            min-height: 80px;
            background-color: #FF4B4B !important;
            color: #ffffff !important;
            font-size: 1.5rem !important;
            font-weight: 800 !important;
            border-radius: 14px;
            border: 3px solid #ffffff;
        }
        .stButton > button:hover { background-color: #e03e3e !important; }

        /* Large, clearly-bordered input fields (easy touch targets) */
        .stTextInput input, .stNumberInput input,
        .stSelectbox div[data-baseweb="select"], .stTextArea textarea {
            font-size: 1.2rem !important;
            padding: 12px !important;
            border: 2px solid #4CAF50 !important;
            border-radius: 10px !important;
        }

        /* Unmistakable online/offline state banner */
        .status-banner {
            padding: 18px; border-radius: 10px; font-weight: 800;
            text-align: center; margin-bottom: 18px; font-size: 1.3rem;
            letter-spacing: 0.5px;
        }
        .status-online  { background-color: #064E3B; color: #6EE7B7; border: 2px solid #10B981; }
        .status-offline { background-color: #7F1D1D; color: #FCA5A5; border: 2px solid #EF4444; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🛰️ Sahar-Connect — Desert Emergency Dispatch")
st.caption("Offline-first neighbour-to-neighbour alerting for Al Qua'a")

# --- 1. Health -------------------------------------------------------------
try:
    health = requests.get(f"{EDGE_API_URL}/health", timeout=3).json()
    location = str(health.get("location", "unknown")).upper()
    st.markdown(
        f'<div class="status-banner status-online">🟢 EDGE NODE ACTIVE &amp; ROUTING'
        f' • LOCATION: {location}</div>',
        unsafe_allow_html=True,
    )
except requests.RequestException:
    st.markdown(
        '<div class="status-banner status-offline">🔴 EDGE NODE OFFLINE'
        ' • START IT WITH: uvicorn src.edge_api.main:app --reload</div>',
        unsafe_allow_html=True,
    )
    st.stop()


def fetch(path):
    try:
        return requests.get(f"{EDGE_API_URL}{path}", timeout=5).json()
    except requests.RequestException:
        return []


responders = fetch("/responders")
alerts = fetch("/alerts")

col_map, col_form = st.columns([2, 1])

# --- 2. Map ----------------------------------------------------------------
with col_map:
    st.subheader("Community map")
    points = []
    for r in responders:
        points.append({"lat": r["lat"], "lon": r["lon"]})
    for a in alerts:
        if not a["resolved"]:
            points.append({"lat": a["lat"], "lon": a["lon"]})
    if points:
        st.map(pd.DataFrame(points), zoom=9)
    else:
        st.info("No data yet — run `python -m src.ai_modules.generate_mock_data`.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Responders", len(responders))
    c2.metric("Available", sum(1 for r in responders if r["available"]))
    c3.metric("Open alerts", sum(1 for a in alerts if not a["resolved"]))

# --- 3. Raise an alert -----------------------------------------------------
with col_form:
    st.subheader("🚨 Raise an emergency")
    with st.form("alert_form", clear_on_submit=True):
        farmer_name = st.text_input("Your name", "Anonymous Farmer")
        lat = st.number_input("Latitude", value=23.55, format="%.5f")
        lon = st.number_input("Longitude", value=55.50, format="%.5f")
        description = st.text_input("Landmark / description",
                                    "e.g. 3km N of the red dune")
        urgency = st.selectbox("Urgency", ["HIGH", "CRITICAL"])
        submitted = st.form_submit_button("Send alert")

        if submitted:
            payload = {
                "farmer_name": farmer_name,
                "lat": lat,
                "lon": lon,
                "description": description,
                "urgency": urgency,
            }
            resp = requests.post(
                f"{EDGE_API_URL}/alerts/create", json=payload, timeout=5
            ).json()
            st.success(f"Alert #{resp['alert_id']} — {resp['status']}")
            if resp.get("distance_km") is not None:
                st.info(
                    f"Nearest responder: **{resp['closest_responder']}** "
                    f"({resp['responder_type']}) — {resp['distance_km']} km away"
                )
            else:
                st.warning(resp["closest_responder"])

# --- 4. Alert log ----------------------------------------------------------
st.subheader("Alert log")
if alerts:
    st.dataframe(pd.DataFrame(alerts), use_container_width=True)
else:
    st.info("No alerts yet.")
