"""
sync_worker.py — the "sync-when-online" half of the offline-first loop.

The edge node saves every alert locally. This worker periodically checks whether
the central cloud is reachable and, when it is, pushes alerts that haven't been
synced yet (is_synced_to_cloud == False) and marks them done. This guarantees
zero data loss while the desert signal is down, and automatic catch-up when it
returns.

The cloud upload is a STUB for now (no central server exists yet), but the
structure is real so the live call drops straight in later. Run standalone:

    python -m src.sync_engine.sync_worker
"""

import os
import time

import requests

from src.edge_api.database import EmergencyAlert, SessionLocal

CLOUD_BASE_URL = os.getenv("CLOUD_BASE_URL", "http://localhost:9000")
CHECK_INTERVAL_SECONDS = int(os.getenv("SYNC_INTERVAL", "15"))


def is_cloud_reachable() -> bool:
    """Return True if the central cloud answers a health check quickly."""
    try:
        resp = requests.get(f"{CLOUD_BASE_URL}/health", timeout=3)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def push_to_cloud(alert: EmergencyAlert) -> bool:
    """
    Send one alert to the cloud. STUB for now — returns True to simulate success.
    Replace the body with a real requests.post(...) once the central API exists.
    """
    # resp = requests.post(f"{CLOUD_BASE_URL}/ingest-alert",
    #                      json={"id": alert.id, "lat": alert.latitude,
    #                            "lon": alert.longitude, "urgency": alert.urgency_level},
    #                      timeout=10)
    # return resp.status_code == 200
    return True


def flush_alerts() -> int:
    """Push every un-synced alert. Returns how many were synced this pass."""
    db = SessionLocal()
    synced = 0
    try:
        pending = (
            db.query(EmergencyAlert)
            .filter(EmergencyAlert.is_synced_to_cloud.is_(False))
            .all()
        )
        for alert in pending:
            if push_to_cloud(alert):
                alert.is_synced_to_cloud = True
                synced += 1
        db.commit()
    finally:
        db.close()
    return synced


def run_forever() -> None:
    print(f"[sync] worker started — cloud target: {CLOUD_BASE_URL}")
    while True:
        if is_cloud_reachable():
            count = flush_alerts()
            print(f"[sync] cloud online — synced {count} alert(s)")
        else:
            print("[sync] cloud offline — holding alerts locally")
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_forever()
