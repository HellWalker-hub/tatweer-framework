"""
app.py — Sahar-Connect emergency dashboard (Streamlit).

Kiosk/operator UI that talks to the edge API and proves the whole loop:
  health -> map of responders & emergencies -> raise an alert -> nearest
  responder dispatched, with a simulated SMS notification.

Phase-1 UX:
  - location capture: tap the map (offline-robust) or "Simulate GPS ping"
  - map clarity: green responders, red emergencies, blue dispatch route
  - feedback loop: simulated SMS payload + responder view

Run it (with the edge API also running):
    streamlit run src/dashboard/app.py
"""

import os
import random

import folium
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium

EDGE_API_URL = os.getenv("EDGE_API_URL", "http://localhost:8000")
AL_QUAA = (23.55, 55.50)        # community centre (lat, lon)
ASSUMED_SPEED_KMH = 40          # desert response vehicle, used for ETA estimates

st.set_page_config(page_title="Sahar-Connect", page_icon="🛰️", layout="wide")

# --- Kiosk accessibility styling -------------------------------------------
# High contrast, large fonts, and big touch targets so the dashboard is usable
# by rural residents on a sun-glared kiosk screen or a phone in the field.
st.markdown(
    """
    <style>
        html { font-size: 18px; }
        h1 { font-size: 2.4rem !important; }
        label, .stMarkdown p { font-size: 1.15rem !important; }

        /* Massive, high-contrast emergency button */
        .stButton > button, .stFormSubmitButton > button {
            width: 100%;
            min-height: 64px;
            font-size: 1.3rem !important;
            font-weight: 800 !important;
            border-radius: 14px;
        }
        .stFormSubmitButton > button {
            background-color: #FF4B4B !important;
            color: #ffffff !important;
            min-height: 80px;
            border: 3px solid #ffffff;
        }
        .stFormSubmitButton > button:hover { background-color: #e03e3e !important; }

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

        /* Simulated SMS dispatch payload */
        .sms-payload {
            background-color: #0F172A; color: #93C5FD; border: 2px dashed #3B82F6;
            border-radius: 10px; padding: 14px; margin-top: 12px;
            font-family: ui-monospace, Menlo, monospace; font-size: 1.0rem; line-height: 1.6;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🛰️ Sahar-Connect — Desert Emergency Dispatch")
st.caption("Offline-first neighbour-to-neighbour alerting for Al Qua'a")

# --- session state ---------------------------------------------------------
st.session_state.setdefault("lat_input", AL_QUAA[0])
st.session_state.setdefault("lon_input", AL_QUAA[1])
st.session_state.setdefault("last_dispatch", None)      # for the map route line
st.session_state.setdefault("last_notification", None)  # for the SMS panel

# --- health (styled, honest online/offline state) --------------------------
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

# --- map: green responders, red emergencies, blue dispatch route -----------
with col_map:
    st.subheader("Community map")

    fmap = folium.Map(location=AL_QUAA, zoom_start=11, control_scale=True)

    for r in responders:
        available = r["available"]
        colour = "#10B981" if available else "#9CA3AF"
        folium.CircleMarker(
            location=[r["lat"], r["lon"]],
            radius=6,
            color=colour,
            fill=True,
            fill_color=colour,
            fill_opacity=0.85,
            tooltip=f"{r['name']} — {'available' if available else 'busy'} ({r['type']})",
        ).add_to(fmap)

    for a in alerts:
        if not a["resolved"]:
            folium.Marker(
                location=[a["lat"], a["lon"]],
                icon=folium.Icon(color="red", icon="exclamation-sign"),
                tooltip=f"🚨 {a['farmer_name']} — {a['urgency']}: {a['landmark'] or ''}",
            ).add_to(fmap)

    dispatch = st.session_state.last_dispatch
    if dispatch and dispatch.get("responder_lat") is not None:
        folium.PolyLine(
            [
                [dispatch["alert_lat"], dispatch["alert_lon"]],
                [dispatch["responder_lat"], dispatch["responder_lon"]],
            ],
            color="#3B82F6",
            weight=4,
            opacity=0.9,
            dash_array="8",
            tooltip=f"Dispatch route → {dispatch['name']} ({dispatch['distance']} km)",
        ).add_to(fmap)

    map_state = st_folium(fmap, height=440, returned_objects=["last_clicked"])

    # Tap-to-place: a click sets the emergency location (works fully offline).
    if map_state and map_state.get("last_clicked"):
        st.session_state.lat_input = round(map_state["last_clicked"]["lat"], 5)
        st.session_state.lon_input = round(map_state["last_clicked"]["lng"], 5)

    st.caption(
        "🟢 responder available · ⚪ busy · 🔴 emergency · 🔵 dispatch route — "
        "**tap the map** to set the emergency location."
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Responders", len(responders))
    c2.metric("Available", sum(1 for r in responders if r["available"]))
    c3.metric("Open alerts", sum(1 for a in alerts if not a["resolved"]))

# --- raise an alert --------------------------------------------------------
with col_form:
    st.subheader("🚨 Raise an emergency")

    # Simulate a hardware GPS ping (drops within ~5 km of Al Qua'a). On a real
    # phone this is replaced by the device GPS; tap-to-place is the offline path.
    if st.button("🎲 Simulate GPS ping (demo)"):
        st.session_state.lat_input = round(AL_QUAA[0] + random.uniform(-0.045, 0.045), 5)
        st.session_state.lon_input = round(AL_QUAA[1] + random.uniform(-0.045, 0.045), 5)
        st.rerun()

    st.caption(
        f"📍 Location: **{st.session_state.lat_input:.5f}, "
        f"{st.session_state.lon_input:.5f}**"
    )

    with st.form("alert_form", clear_on_submit=False):
        farmer_name = st.text_input("Your name", "Anonymous Farmer")
        lat = st.number_input("Latitude", format="%.5f", key="lat_input")
        lon = st.number_input("Longitude", format="%.5f", key="lon_input")
        description = st.text_input("Landmark / description", "e.g. 3km N of the red dune")
        urgency = st.selectbox("Urgency", ["HIGH", "CRITICAL"])
        submitted = st.form_submit_button("🚨 Send alert")

    if submitted:
        payload = {
            "farmer_name": farmer_name,
            "lat": lat,
            "lon": lon,
            "description": description,
            "urgency": urgency,
        }
        try:
            resp = requests.post(
                f"{EDGE_API_URL}/alerts/create", json=payload, timeout=5
            ).json()
        except requests.RequestException as exc:
            st.error(f"Could not reach edge API: {exc}")
            resp = None

        if resp:
            dist = resp.get("distance_km")
            eta = round(dist / ASSUMED_SPEED_KMH * 60) if dist else None
            st.session_state.last_dispatch = {
                "alert_lat": lat,
                "alert_lon": lon,
                "responder_lat": resp.get("responder_lat"),
                "responder_lon": resp.get("responder_lon"),
                "name": resp.get("closest_responder"),
                "distance": dist,
            }
            st.session_state.last_notification = {
                "alert_id": resp.get("alert_id"),
                "name": resp.get("closest_responder"),
                "rtype": resp.get("responder_type"),
                "dist": dist,
                "eta": eta,
                "phone": "+971 50 945 5277",
                "lat": lat,
                "lon": lon,
                "urgency": urgency,
            }
            st.rerun()

    # Feedback loop: persistent "last dispatch" panel with a simulated SMS.
    note = st.session_state.last_notification
    if note:
        if note["dist"] is not None:
            st.success(
                f"✅ Alert #{note['alert_id']} dispatched → **{note['name']}** "
                f"({note['rtype']}) · {note['dist']} km · ETA ~{note['eta']} min"
            )
            st.markdown(
                '<div class="sms-payload">📨 SMS PAYLOAD GENERATED<br>'
                f'To: {note["phone"]}<br>'
                f'{note["urgency"]} alert at {note["lat"]:.5f}, {note["lon"]:.5f}<br>'
                f'Nearest unit: {note["name"]} · ETA ~{note["eta"]} min</div>',
                unsafe_allow_html=True,
            )
            st.caption(
                "Simulated payload — this is the exact message handed to an SMS gateway "
                "(e.g. Twilio) the moment the node regains connectivity."
            )
            with st.expander("📟 Responder view — what the dispatched unit receives"):
                st.markdown(f"### 🚨 {note['urgency']} ALERT")
                st.write(f"**Assigned to:** {note['name']} ({note['rtype']})")
                st.write(f"**Location:** {note['lat']:.5f}, {note['lon']:.5f}")
                st.write(f"**Distance:** {note['dist']} km · **ETA:** ~{note['eta']} min")
                st.map(pd.DataFrame([{"lat": note["lat"], "lon": note["lon"]}]), zoom=11)
        else:
            st.warning(f"Alert #{note['alert_id']} logged — broadcast to all neighbours.")

# --- alert log -------------------------------------------------------------
st.subheader("Alert log")
if alerts:
    st.dataframe(pd.DataFrame(alerts), use_container_width=True)
else:
    st.info("No alerts yet.")
