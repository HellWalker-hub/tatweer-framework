"""
app.py — Streamlit dashboard / kiosk UI.

A tiny front-end that proves the whole loop works end-to-end:
  1. shows whether the edge API is online,
  2. lets someone submit a request, and
  3. lists everything currently saved in the local queue.

Run it with (while the edge API is also running):
    streamlit run src/dashboard/app.py
"""

import json
import os

import requests
import streamlit as st

EDGE_API_URL = os.getenv("EDGE_API_URL", "http://localhost:8000")

st.set_page_config(page_title="Tatweer Edge Kiosk", page_icon="🛰️")
st.title("Tatweer — Rural Edge Kiosk")

# --- 1. Health -------------------------------------------------------------
try:
    health = requests.get(f"{EDGE_API_URL}/health", timeout=3).json()
    st.success(f"Edge node ONLINE · location: {health.get('location', 'unknown')}")
except requests.RequestException:
    st.error(f"Edge API not reachable at {EDGE_API_URL}. Is uvicorn running?")
    st.stop()

# --- 2. Submit a request ---------------------------------------------------
st.subheader("Submit a request")
with st.form("submit_form", clear_on_submit=True):
    req_type = st.selectbox(
        "Request type",
        ["service_request", "logistics_update", "generic"],
    )
    name = st.text_input("Name")
    note = st.text_area("Details")
    submitted = st.form_submit_button("Submit")

    if submitted:
        payload = {"type": req_type, "data": {"name": name, "note": note}}
        resp = requests.post(
            f"{EDGE_API_URL}/submit-request", json=payload, timeout=5
        ).json()
        st.success(f"Saved locally (queue id #{resp.get('queue_id')})")

# --- 3. Local queue contents ----------------------------------------------
# Read the local SQLite directly so the dashboard works even with no cloud.
st.subheader("Local queue (offline-first store)")
try:
    from src.edge_api.database import LocalQueue, SessionLocal

    db = SessionLocal()
    rows = db.query(LocalQueue).order_by(LocalQueue.id.desc()).all()
    db.close()
    if rows:
        st.dataframe(
            [
                {
                    "id": r.id,
                    "type": r.payload_type,
                    "data": json.loads(r.data_payload or "{}"),
                    "time": r.timestamp,
                    "synced": r.is_synced,
                }
                for r in rows
            ],
            use_container_width=True,
        )
    else:
        st.info("Queue is empty — submit a request above.")
except Exception as exc:  # noqa: BLE001 — surface any DB issue to the kiosk user
    st.warning(f"Could not read local queue: {exc}")
