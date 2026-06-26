"""
download_tiles.py — pre-fetch satellite map tiles for the Al Qua'a area so the
dashboard map works **fully offline** (served by the edge node, no internet).

Uses **Esri World Imagery** (satellite), which permits this use with attribution
and looks far better for a desert region than a street map. (OpenStreetMap's
volunteer servers forbid bulk downloading and return "Access blocked" tiles.)

Downloads a tight bounding box around Al Qua'a at zoom 11-15 into
    local_data/tiles/{z}/{x}/{y}.png
which the edge API then serves at /tiles (see src/edge_api/main.py), and which
the dashboard points to via the TILE_SERVER_URL env var.

Run once (needs internet):
    python -m src.utils.download_tiles

Re-runnable: existing tiles are skipped.
Attribution required in the UI: "Tiles © Esri — World Imagery".
"""

import math
import os
import time

import requests

# Tight bounding box around Al Qua'a (covers the responder cluster + surrounds).
MIN_LAT, MAX_LAT = 23.40, 23.75
MIN_LON, MAX_LON = 55.30, 55.70
ZOOMS = range(11, 16)  # 11..15

# Esri World Imagery uses {z}/{y}/{x} tile order (row before column).
TILE_URL = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/{z}/{y}/{x}"
)
HEADERS = {"User-Agent": "Sahar-Connect/1.0 (Tatweer Hackathon offline edge node)"}
REQUEST_DELAY_S = 0.03  # Esri is a robust CDN; a small delay keeps us polite

OUT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "local_data", "tiles")
)


def deg2tile(lat: float, lon: float, zoom: int):
    """Slippy-map: lat/lon -> (x, y) tile indices at a zoom level."""
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n)
    return x, y


def tile_ranges(zoom: int):
    x0, y0 = deg2tile(MAX_LAT, MIN_LON, zoom)  # top-left
    x1, y1 = deg2tile(MIN_LAT, MAX_LON, zoom)  # bottom-right
    xs = range(min(x0, x1), max(x0, x1) + 1)
    ys = range(min(y0, y1), max(y0, y1) + 1)
    return xs, ys


def main():
    # Plan first so the user sees the size before any download.
    plan = {}
    total = 0
    for z in ZOOMS:
        xs, ys = tile_ranges(z)
        plan[z] = (xs, ys)
        n = len(xs) * len(ys)
        total += n
        print(f"  zoom {z}: {len(xs)} x {len(ys)} = {n} tiles")
    print(f"TOTAL ~{total} tiles -> {OUT_DIR}\n")

    fetched = skipped = failed = 0
    for z in ZOOMS:
        xs, ys = plan[z]
        for x in xs:
            d = os.path.join(OUT_DIR, str(z), str(x))
            os.makedirs(d, exist_ok=True)
            for y in ys:
                path = os.path.join(d, f"{y}.png")
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    skipped += 1
                    continue
                try:
                    r = requests.get(
                        TILE_URL.format(z=z, x=x, y=y), headers=HEADERS, timeout=20
                    )
                    if r.status_code == 200 and r.content:
                        with open(path, "wb") as f:
                            f.write(r.content)
                        fetched += 1
                    else:
                        failed += 1
                        print(f"    {z}/{x}/{y} -> HTTP {r.status_code}")
                    time.sleep(REQUEST_DELAY_S)
                except requests.RequestException as exc:
                    failed += 1
                    print(f"    {z}/{x}/{y} error: {exc}")
        print(f"  zoom {z} complete (fetched={fetched} skipped={skipped} failed={failed})")

    size_mb = sum(
        os.path.getsize(os.path.join(dp, f))
        for dp, _, fs in os.walk(OUT_DIR)
        for f in fs
    ) / (1024 * 1024)
    print(f"\nDone. fetched={fetched} skipped={skipped} failed={failed} | {size_mb:.1f} MB on disk")


if __name__ == "__main__":
    main()
