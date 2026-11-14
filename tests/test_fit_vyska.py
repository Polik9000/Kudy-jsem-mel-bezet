"""tools/fit_vyska.py: the shift search finds a known shift of the track on hilly made-up terrain and does not
trust itself on flat ground; the comparison with the terrain gives back the offset and drift of the barometer."""
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fit_vyska as fv  # noqa: E402

LAT0, LON0 = 49.5, 17.0
KX = fv.R_EARTH * math.cos(math.radians(LAT0)) * math.pi / 180
KY = fv.R_EARTH * math.pi / 180


class Terrain:
    """height(lat, lon) of a made-up landscape (metres east/north of LAT0, LON0)."""
    source = "test"

    def __init__(self, f):
        self.f = f

    def height(self, lat, lon):
        x = (np.asarray(lon, float) - LON0) * KX
        y = (np.asarray(lat, float) - LAT0) * KY
        return self.f(x, y)


HILLS = Terrain(lambda x, y: 25 * np.sin(x / 70.0) + 18 * np.cos(y / 55.0) + 6 * np.sin((x + y) / 23.0))
FLAT = Terrain(lambda x, y: 300.0 + 0.0 * x)


def run(terrain, gps_error=(12.0, -8.0), offset=-40.0, drift_per_h=6.0, seconds=1500):
    """A run of `seconds` at 3 m/s on a wandering line; the barometer reads the terrain where the runner really
    was (plus offset and drift), the GPS positions are off by gps_error metres."""
    t = np.arange(seconds, dtype=float)
    heading = 0.6 * np.sin(t / 90.0) + 0.3 * np.sin(t / 37.0)
    x = np.cumsum(3.0 * np.cos(heading))
    y = np.cumsum(3.0 * np.sin(heading)) + 40 * np.sin(t / 200.0)
    lat, lon = LAT0 + y / KY, LON0 + x / KX
    alt = terrain.height(lat, lon) + offset + drift_per_h * t / 3600.0
    gx, gy = x + gps_error[0], y + gps_error[1]
    return dict(t=t, lat=LAT0 + gy / KY, lon=LON0 + gx / KX, alt=alt)


def test_compare_gives_back_offset_and_drift():
    s = run(HILLS, gps_error=(0.0, 0.0))
    v = fv.compare(s, HILLS)
    assert abs(v["offset_m"] - (-40 + 6 * 750 / 3600)) < 0.5
    assert abs(v["drift_m_per_h"] - 6.0) < 0.3
    assert v["rms_drift_m"] < 0.2 and v["slope_corr"] > 0.99


def test_shift_found_on_hills():
    s = run(HILLS)
    found = fv.search(s, HILLS)
    w = found["whole"]
    # the shift that brings the GPS back to where the runner was: minus the GPS error
    assert (w["dx"], w["dy"]) == (-12.0, 8.0)
    assert fv.confident(w) and not fv.nonsense(w)
    assert found["windows"] and all(r["trusted"] for r in found["windows"])
    assert np.allclose(found["shift_x"], -12.0) and np.allclose(found["shift_y"], 8.0)


def test_no_shift_trusted_on_flat_ground():
    s = run(FLAT)
    found = fv.search(s, FLAT)
    assert not fv.confident(found["whole"])
    assert not any(r["trusted"] for r in found["windows"])
    assert not found["shift_x"].any() and not found["shift_y"].any()


def test_windows_overlap_by_half_and_cover_the_track():
    w = fv.windows(np.array([0.0, 1000.0, 2100.0]), 800.0)
    assert w[0] == (0.0, 800.0) and w[1] == (400.0, 1200.0) and w[-1][1] == 2100.0
    assert fv.windows(np.array([0.0, 500.0]), 800.0) == [(0.0, 500.0)]
