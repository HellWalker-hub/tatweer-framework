# 🛰️ Sahar-Connect: Desert Emergency Dispatch

**Tatweer Hackathon 2026 Submission** | **Track:** Solutions for rural communities (Challenge 2)

Sahar-Connect is an offline-first, edge-native dispatch framework designed to shorten the gap
between a critical need arising in a dispersed rural setting and the right response reaching the
person. It is built specifically for the geographical realities of Al Qua'a.

![Sahar-Connect Dashboard](docs/dashboard.png)

---

## 1. The Challenge & The Problem (Criterion 2)
**Challenge 2: Reaching people quickly across a dispersed community.**
Standard city-centric dispatch tools rely on named streets and continuous 5G/cloud connectivity.
In rural, dispersed communities like Al Qua'a — where camel farms are spread across desert
fringes — emergencies (vehicle breakdowns in dunes, injured livestock, rapid-onset sandstorms)
happen off the grid. Centralized dispatch fails when addresses don't exist and the connection drops.

## 2. Target Demographic & Impact (Criterion 1)
**Who it is for:** The residents and farmers of Al Qua'a, specifically those managing livestock
off the main grid, and the local volunteer / civil-defence responders.

**The impact:** Sahar-Connect shifts emergency response from a "call and wait for central
dispatch" model to a "localized neighbour-to-neighbour mesh" model. It identifies the closest
available responder using offline geographic math, cutting critical response time in an
environment where distance and dispersion normally work against speed.

## 3. Our Solution & Testable Claims (Criterion 6)
Sahar-Connect is a localized edge API and kiosk UI that logs distress signals and routes them to
the nearest available responder without a cloud round-trip.

**Testable claims (falsifiability):**
- **Claim 1 — Dispatch needs no external map API.** The closest responder is computed with the
  pure Haversine formula over stored coordinates, in milliseconds, using only the Python standard
  library. *Verify:* `pytest` runs the `routing.py` unit tests (4/4) asserting distance and
  nearest-responder correctness.
- **Claim 2 — Capture and dispatch work fully offline.** Alerts are written to a local SQLite
  store and dispatched by local math; no internet is required for the core flow. *Verify:*
  disable Wi-Fi, raise an alert — it is logged and a nearest responder is returned. (The map
  *tiles* are the only online-dependent visual; the dispatch logic does not depend on them.)
- **Claim 3 — Deterministic, fast cold-start.** Because it is decoupled from any consumer
  cloud-sync layer, the edge node boots and serves the UI in seconds on commodity hardware.

## 4. Feasibility & Readiness (Criteria 3 & 4)
**Readiness:** Complete and demonstrable end-to-end — backend API, geospatial routing engine,
Streamlit kiosk dashboard, and a reproducible seed of **53 responder nodes** placed around Al
Qua'a's real coordinates (deterministic, `seed=42`).

**Deployment feasibility:** This is not a heavy cloud application. It is designed to run on a
low-cost edge device (e.g. a Raspberry Pi 5) at a community centre or local telecom mast. It uses
standard Python libraries — no GPU, no enterprise cloud licensing.

## 5. Scalability After the Hackathon (Criterion 5)
Built for the Al Qua'a pilot, but the architecture is inherently replicable. Each community runs
its own self-contained edge node; scaling means deploying another node elsewhere (e.g. Liwa or
Madinat Zayed). When connectivity allows, the sync engine pushes incident logs up to a central
municipal server — creating a resilient, nation-wide rural safety net from independent local nodes.

---

## 🏗️ Architecture

```
[ Farmer / Kiosk UI ]            Streamlit dashboard (touch-friendly)
          │  raise alert (tap location + describe)
          ▼
[ Edge API  ·  FastAPI ]         runs locally on the edge node
          │  1. save to local store (never lost offline)
          │  2. Haversine -> nearest available responder
          ▼
[ Local store · SQLite ]  --->  [ Sync engine ]  --->  [ Central server ]
   alerts + responders           when online, flush        (future / record-keeping)
                                 unsynced alerts
```

**In one sentence:** Sahar-Connect replaces a centralized cloud dispatch system with a localized,
offline-resilient microservice that runs on cheap hardware directly in the community.

---

## ⚙️ How to Run and Verify (Criterion 7)

**Prerequisites:** Python 3.10+

**1. Clone & set up the environment**
```bash
git clone https://github.com/HellWalker-hub/tatweer-framework.git
cd tatweer-framework
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**2. Run the tests** (verifies the offline routing math — Claim 1)
```bash
pytest -q          # expect: 4 passed
```

**3. Seed the Al Qua'a database** (53 responder nodes + sample alerts)
```bash
python -m src.ai_modules.generate_mock_data
```

**4. Start the edge API** (terminal 1)
```bash
uvicorn src.edge_api.main:app --reload      # http://localhost:8000/docs
```

**5. Start the kiosk dashboard** (terminal 2)
```bash
streamlit run src/dashboard/app.py          # http://localhost:8501
```

Open `http://localhost:8501`. To prove the offline claim: disconnect from the internet, raise an
alert, and confirm it is logged and a nearest responder is dispatched.

> **Note on commands:** the seeder and sync worker are Python packages, so run them with `python -m`
> (module form), not `python src/...` — the module form sets up the package imports correctly.

---

## 🧰 Tools
Built with **FastAPI**, **Streamlit**, **SQLAlchemy/SQLite**, and **pandas**. Geospatial routing
uses the standard-library Haversine formula. No ML/GPU dependencies.

## 📄 License / Open source
Released publicly as required by the Tatweer Hackathon. The framework is intended to be reusable
by other rural communities across the UAE.

_Tatweer Hackathon · Al Qua'a, Al Ain · 2026_
