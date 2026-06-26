"""
Unit tests for the geo-routing math. These back our dispatch-accuracy claims
with reproducible evidence (hackathon Criterion 6 — falsifiability).

Run with:  python -m pytest -q
"""

from types import SimpleNamespace

from src.edge_api.routing import find_nearest_responder, haversine_distance


def test_haversine_known_distance():
    # One degree of longitude at the equator is ~111.19 km.
    d = haversine_distance(0.0, 0.0, 0.0, 1.0)
    assert abs(d - 111.19) < 0.5


def test_haversine_zero_for_same_point():
    assert haversine_distance(23.55, 55.50, 23.55, 55.50) == 0.0


def test_nearest_picks_closest():
    here = (23.55, 55.50)
    responders = [
        SimpleNamespace(responder_name="far", current_lat=24.00, current_lon=56.00),
        SimpleNamespace(responder_name="near", current_lat=23.56, current_lon=55.51),
        SimpleNamespace(responder_name="mid", current_lat=23.70, current_lon=55.60),
    ]
    nearest, dist = find_nearest_responder(*here, responders)
    assert nearest.responder_name == "near"
    assert dist < 2.0  # the "near" farm is within ~2 km


def test_nearest_handles_empty_list():
    nearest, dist = find_nearest_responder(23.55, 55.50, [])
    assert nearest is None
    assert dist is None
