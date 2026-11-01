"""OpenStreetMap barriers and ČÚZK elevation, tested on answers saved in tests/fixtures (no network)."""
import json
import os

import numpy as np
import pytest
from races import ROOT, inputs

from oroute import dem, osm

FIX = os.path.join(ROOT, "tests", "fixtures")


def overpass():
    with open(os.path.join(FIX, "osm", "petrvald_overpass.json"), encoding="utf-8") as f:
        return json.load(f)


def test_query_asks_once_for_everything():
    q = osm.query(49.82, 18.35, 49.85, 18.39)
    assert q.startswith("[out:json]") and "(49.820000,18.350000,49.850000,18.390000)" in q
    for piece in ('"railway"~"^(rail|', '"highway"~"^(motorway|', '"barrier"~"^(fence|', "level_crossing", '["bridge"]',
                  '["tunnel"]', "out body geom"):
        assert piece in q


def test_parse_petrvald():
    d = osm.parse(overpass())
    rails = [l for l in d["lines"] if l["what"] == "railway"]
    assert len(rails) == 2 and all(l["kind"] == "forbidden" and len(l["line"]) >= 2 for l in rails)
    assert all(l["kind"] == "hard" for l in d["lines"] if l["what"] == "fence")
    assert len(d["crossings"]) == 3
    # the crossings lie on the railway (within a few metres of one of its vertices or segments)
    pts = np.array([p for l in rails for p in l["line"]])
    for la, lo in d["crossings"]:
        m = np.hypot((pts[:, 0] - la) * 111195, (pts[:, 1] - lo) * 111195 * 0.645).min()
        assert m < 120
    assert osm.parse(overpass(), fences=False)["lines"] == rails


def way(tags, pts):
    return dict(type="way", tags=tags, geometry=[dict(lat=a, lon=b) for a, b in pts])


def test_bridges_and_tunnels():
    rail = way(dict(railway="rail"), [(50.0, 14.0), (50.0, 14.01)])
    viaduct = way(dict(railway="rail", bridge="yes"), [(50.0, 14.01), (50.0, 14.02)])
    underpass = way(dict(highway="footway", tunnel="yes"), [(49.999, 14.005), (50.001, 14.005)])
    road = way(dict(highway="track"), [(49.999, 14.007), (50.001, 14.007)])       # at grade, no crossing mapped
    motorway = way(dict(highway="motorway"), [(50.01, 14.0), (50.01, 14.02)])
    over = way(dict(highway="tertiary", bridge="yes"), [(50.009, 14.01), (50.011, 14.01)])
    node = dict(type="node", lat=50.0, lon=14.002, tags=dict(railway="level_crossing"))
    d = osm.parse(dict(elements=[rail, viaduct, underpass, road, motorway, over, node]))
    assert [(l["what"], l["kind"]) for l in d["lines"]] == [("railway", "forbidden"), ("motorway", "forbidden")]
    assert d["lines"][0]["line"] == [[50.0, 14.0], [50.0, 14.01]]                  # the viaduct is left out
    assert sorted(d["crossings"]) == [[50.0, 14.002], [50.0, 14.005], [50.01, 14.01]]
    assert osm.parse(dict(elements=[])) == dict(lines=[], crossings=[])


def test_fetch_gives_up_politely(monkeypatch):
    calls = []

    def boom(req, timeout=0):
        calls.append(req.full_url)
        raise OSError("504 Gateway Timeout")
    monkeypatch.setattr(osm.urllib.request, "urlopen", boom)
    with pytest.raises(OSError, match="Overpass"):
        osm.fetch(49.8, 18.3, 49.9, 18.4, retries=1, pause=0)
    assert calls == [osm.OVERPASS] * 2 + [osm.FALLBACK] * 2         # the same rules on the second server


def test_fetch_asks_the_second_server_when_the_first_is_busy(monkeypatch):
    import io
    import urllib.error
    calls = []

    def answer(req, timeout=0):
        calls.append((req.full_url, req.get_header("User-agent")))
        if req.full_url == osm.OVERPASS:
            raise urllib.error.HTTPError(req.full_url, 502, "Bad Gateway", {}, None)
        return io.BytesIO(json.dumps(overpass()).encode())
    monkeypatch.setattr(osm.urllib.request, "urlopen", answer)
    got = osm.for_box(49.8, 18.3, 49.9, 18.4, retries=2, pause=0)
    assert got["lines"] and [c[0] for c in calls] == [osm.OVERPASS] * 3 + [osm.FALLBACK]
    assert {c[1] for c in calls} == {osm.AGENT}


def test_user_is_told_plainly_when_openstreetmap_is_down(tmp_path):
    from types import SimpleNamespace

    from webapp.services import runner

    def down(*box):
        raise OSError("Overpass: HTTP Error 502: Bad Gateway")
    conf = SimpleNamespace(osm=True, osm_fetch=down, path=lambda *p: str(tmp_path.joinpath(*p)))
    kmz = inputs("petrvald")[1]
    note = runner.fetch_osm(conf, 1, kmz)
    assert note == ("OpenStreetMap teď neodpovídá (přetížený server). Zakázané přechody se doplní při příštím "
                    "přepočtu.")
    assert "502" not in note and "HTTP" not in note


# --- ČÚZK DMR 5G -----------------------------------------------------------------------------------------

BOX = dict(north=49.8310, south=49.8300, east=18.3715, west=18.3700)


def stored(*a, **k):
    with open(os.path.join(FIX, "cuzk", "dmr5g_petrvald.tif"), "rb") as f:
        return f.read()


def test_cuzk_reads_a_stored_answer(tmp_path):
    asked = []

    def fetch(s, n, w, e, width, height):
        asked.append((s, n, w, e, width, height))
        return stored()
    d = dem.CuzkDEM(fetch=fetch, cache=str(tmp_path / "dem_cuzk.npz"), **BOX)
    s, n, w, e, width, height = asked[0]
    assert s < BOX["south"] and n > BOX["north"] and w < BOX["west"] and e > BOX["east"]     # padded
    assert (width, height) == (142, 93)          # pixels square in degrees, about 2.5 m in latitude
    assert d.source == "cuzk" and d.h.shape == (93, 142)
    h = d.height(np.array([49.8305, 49.8309]), np.array([18.37075, 18.3702]))
    assert 250 < h.min() and h.max() < 270       # Petřvald lies at about 260 m
    # the second time the cache answers, the service is not asked
    again = dem.CuzkDEM(fetch=lambda *a: 1 / 0, cache=str(tmp_path / "dem_cuzk.npz"), **BOX)
    assert np.allclose(again.h, d.h) and abs(again.n - d.n) < 1e-12
    # smoothing is on by default and only removes small bumps
    raw = dem.CuzkDEM(fetch=fetch, smooth_m=0, **BOX)
    assert 0 < np.abs(raw.h - d.h).max() < 4 and abs(raw.h.mean() - d.h.mean()) < 0.2


def test_cuzk_refuses_what_is_not_usable():
    with pytest.raises(dem.DemError):
        dem.CuzkDEM(fetch=lambda *a: b"not a tiff", **BOX)
    with pytest.raises(dem.DemError, match="timed out"):
        def down(*a):
            raise OSError("timed out")
        dem.CuzkDEM(fetch=down, **BOX)
    # an answer for another place does not cover the map
    with pytest.raises(dem.DemError, match="does not cover"):
        dem.CuzkDEM(49.90, 49.89, 18.50, 18.49, fetch=stored)


def test_auto_uses_cuzk_only_inside_czechia(tmp_path, monkeypatch):
    assert dem.in_czechia(49.84, 49.82, 18.39, 18.35)             # Petřvald
    assert not dem.in_czechia(49.97, 49.95, 21.87, 21.84)         # Boguchwała, Poland
    made = []

    class FakeAws:
        source = "aws"

        def __init__(self, *a, cache=None, **k):
            made.append(cache)
    monkeypatch.setattr(dem, "TerrariumDEM", FakeAws)
    monkeypatch.setattr(dem, "_cuzk_fetch", stored)
    out = str(tmp_path)
    assert dem.load_dem(49.97, 49.95, 21.87, 21.84, out, "auto").source == "aws"      # abroad: AWS, ČÚZK not asked
    assert dem.load_dem(BOX["north"], BOX["south"], BOX["east"], BOX["west"], out, "auto").source == "cuzk"
    assert os.path.exists(os.path.join(out, "dem_cuzk.npz"))
    # ČÚZK fails: auto falls back to AWS and says so, "cuzk" raises
    said = []
    assert dem.load_dem(49.90, 49.89, 18.50, 18.49, out, "auto", log=said.append).source == "aws"
    assert "falling back" in said[0]
    with pytest.raises(dem.DemError):
        dem.load_dem(49.90, 49.89, 18.50, 18.49, out, "cuzk")
    assert dem.load_dem(1, 0, 1, 0, out, "aws").source == "aws" and made[-1].endswith("dem_cache.npz")
    with pytest.raises(ValueError):
        dem.load_dem(1, 0, 1, 0, out, "lidar")
