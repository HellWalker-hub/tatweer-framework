"""
sync_worker.py — the "sync-when-online" half of the offline-first loop.

The edge API saves everything locally. This worker periodically checks whether
the central cloud is reachable and, if it is, pushes any rows that haven't been
synced yet and marks them as done.

For now the actual cloud upload is a STUB (there is no central server yet), but
the structure is real so the live call drops straight in later. You can run it
standalone to watch it work:

    python -m src.sync_engine.sync_worker
"""

import os
import time

import requests

from src.edge_api.database import LocalQueue, SessionLocal

# Where the central UAE cloud would live. Overridable via .env / environment.
CLOUD_BASE_URL = os.getenv("CLOUD_BASE_URL", "http://localhost:9000")
CHECK_INTERVAL_SECONDS = int(os.getenv("SYNC_INTERVAL", "15"))


def is_cloud_reachable() -> bool:
    """Return True if the central cloud answers a health check quickly."""
    try:
        resp = requests.get(f"{CLOUD_BASE_URL}/health", timeout=3)
        return resp.status_code == 200
    except requests.RequestException:
        # No connection / timeout / DNS failure -> treat as offline.
        return False


def push_to_cloud(item: LocalQueue) -> bool:
    """
    Send one queued item to the cloud. STUB for now — returns True to simulate a
    successful upload. Replace the body with a real requests.post(...) once the
    central API exists.
    """
    # Example of the real call we'll enable later:
    # resp = requests.post(f"{CLOUD_BASE_URL}/ingest",
    #                      json={"type": item.payload_type, "data": item.data_payload},
    #                      timeout=10)
    # return resp.status_code == 200
    return True


def flush_queue() -> int:
    """Push every un-synced row. Returns how many were synced this pass."""
    db = SessionLocal()
    synced = 0
    try:
        pending = db.query(LocalQueue).filter(LocalQueue.is_synced.is_(False)).all()
        for item in pending:
            if push_to_cloud(item):
                item.is_synced = True
                synced += 1
        db.commit()
    finally:
        db.close()
    return synced


def run_forever() -> None:
    """Loop: when the cloud is reachable, flush the local queue."""
    print(f"[sync] worker started — cloud target: {CLOUD_BASE_URL}")
    while True:
        if is_cloud_reachable():
            count = flush_queue()
            print(f"[sync] cloud online — synced {count} item(s)")
        else:
            print("[sync] cloud offline — holding data locally")
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_forever()
