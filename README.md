# Tatweer Framework

An **offline-first digital infrastructure framework** for rural UAE communities,
built for the **Tatweer Hackathon** (26–28 June 2026, Al Qua'a, Al Ain).

Major cities have comprehensive digital frameworks; many rural communities don't.
The internet at the edge can be slow or absent. So this framework is built around
one core idea:

> **capture locally → store locally → sync to the cloud when a connection exists**

Nothing is ever lost while offline.

## The base idea (this skeleton)

```
[ Kiosk / Dashboard ]  →  [ Edge API ]  →  [ Local SQLite queue ]
                                                     │
                                          [ Sync engine, when online ]
                                                     │
                                              [ Central cloud ]  (future)
```

The specific feature domain (e.g. logistics, service requests, monitoring) is
**not chosen yet** — this base supports any of them without rework.

## Layout

```
src/
├── edge_api/      FastAPI app — runs at the rural site
│   ├── main.py        /health and /submit-request endpoints
│   └── database.py    SQLite + SQLAlchemy local queue
├── sync_engine/   pushes queued data to the cloud when reachable
│   └── sync_worker.py
├── ai_modules/    placeholder — no domain logic yet
└── dashboard/     Streamlit kiosk/admin UI
    └── app.py
```

## Run it locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 1. Start the edge API
uvicorn src.edge_api.main:app --reload      # http://localhost:8000/docs

# 2. In another terminal, start the dashboard
streamlit run src/dashboard/app.py          # http://localhost:8501

# 3. (optional) Run the sync worker
python -m src.sync_engine.sync_worker
```

Configuration lives in `.env` (copy from `.env.example`).

## License / open-source

This project will be made **public and open-source** as required by the
competition. Tools built here are intended to be reusable by other rural
communities across the UAE.
