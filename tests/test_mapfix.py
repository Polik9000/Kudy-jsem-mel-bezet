"""A map placed a few metres off, moved by hand by the controls (services/mapfix.py, georef.shift_kmz)."""
import hashlib
import math
import os
import zipfile

import numpy as np
import pytest
from conftest import csrf, post, register
from PIL import Image
from test_web_races import con_of

from oroute import georef
from oroute.kmzmap import GeoMap
from webapp.seed import seed_demo
from webapp.services import mapfix

LAT0, LON0 = 49.70, 18.30


def _metres(gm, u, v):
    la, lo = gm.px_to_latlon(u, v)
    return np.c_[georef.local_frame(LAT0, LON0)(la, lo)]


def test_shift_kmz_moves_the_box_and_keeps_the_picture(tmp_path):
    img = Image.new("RGB", (400, 300), (250, 250, 250))
    gm = GeoMap(img, 49.701, 49.699, 18.302, 18.298, rotation=3.0, header_px=0)
    src, dst = str(tmp_path / "a.kmz"), str(tmp_path / "b.kmz")
    georef.write_kmz(src, img, gm, png=True)
    corr = (1.01, math.radians(1.5), 20.0, -12.0)
    georef.shift_kmz(src, dst, corr, LAT0, LON0)
    a, b = GeoMap.from_kmz(src), GeoMap.from_kmz(dst)
    px = [(0, 0), (400, 0), (0, 300), (123, 77), (400, 300)]
    want = georef.apply_similarity(corr, _metres(a, [p[0] for p in px], [p[1] for p in px]))
    got = _metres(b, [p[0] for p in px], [p[1] for p in px])
    assert np.abs(got - want).max() < 0.05                      # every pixel moved exactly as the correction says
    with zipfile.ZipFile(src) as za, zipfile.ZipFile(dst) as zb:
        assert za.read("files/map.png") == zb.read("files/map.png")
        assert "ob-header-px: 0" in zb.read("doc.kml").decode()


def test_evaluate_finds_how_far_the_map_is_off():
    img = Image.new("RGB", (1000, 800), (250, 250, 250))
    gm = GeoMap(img, 49.704, 49.696, 18.306, 18.294, rotation=0.0, header_px=0)
    clicked = {"S": (100, 100), "1": (900, 120), "2": (850, 700), "3": (150, 650), "4": (500, 400)}
    true = (1.0, math.radians(-0.8), 25.0, 8.0)                   # the map lies 25 m west and 8 m south of the truth
    now = _metres(gm, [p[0] for p in clicked.values()], [p[1] for p in clicked.values()])
    rng = np.random.default_rng(3)
    ground = {n: tuple(q) for n, q in zip(clicked, georef.apply_similarity(true, now) + rng.normal(0, 4, now.shape))}
    pts = [(n, u, v) for n, (u, v) in clicked.items()]
    out = mapfix.evaluate(gm, 1.0, pts, ground.get, LAT0, LON0, np.zeros((0, 2)))
    assert out["ok"] and out["rms"] < 12 and abs(out["turn_deg"] + 0.8) < 0.5
    assert abs(math.hypot(*out["corr"][2:]) - math.hypot(25, 8)) < 30     # (the translation is about the frame origin)
    assert all(d < 30 for d in out["deviation"].values())
    # one point on the wrong circle is told
    wrong = dict(ground, **{"4": (ground["4"][0] + 120, ground["4"][1])})
    out = mapfix.evaluate(gm, 1.0, pts, wrong.get, LAT0, LON0, np.zeros((0, 2)))
    assert not out["ok"] and out["far"] == ["4"]
    # two points are not enough
    assert not mapfix.evaluate(gm, 1.0, pts[:2], ground.get, LAT0, LON0, np.zeros((0, 2)))["ok"]


def _md5(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


@pytest.mark.needs_data
def test_map_moved_by_hand_and_back(app, client, user):
    from webapp.views.photo import _ground, _where

    con, conf = con_of(app), app.config["OB"]
    entry = seed_demo(con, conf, user)["pohora"]
    e = con.execute("SELECT e.*, c.course_file, c.course_source, c.event_id, ev.maponly_file FROM entries e"
                    " JOIN classes c ON c.id = e.class_id JOIN events ev ON ev.id = c.event_id WHERE e.id = ?",
                    (entry,)).fetchone()
    course, maponly = conf.path(e["course_file"]), conf.path(e["maponly_file"])
    before = _md5(course), _md5(maponly)
    page = client.get(f"/races/{entry}/mapa-rucne")
    assert page.status_code == 200 and "Usadit mapu ručně" in page.get_data(as_text=True)
    assert client.get(f"/races/{entry}/mapa-rucne.jpg").status_code == 200
    # click the controls where the track says they are, as on a map that lies 30 m east of the truth
    with app.test_request_context():
        ground, lat0, lon0, _ = _ground(dict(e))
    _, size, k, gm = mapfix.preview(conf, e["course_file"])
    kx = georef.R_EARTH * math.cos(math.radians(lat0)) * math.pi / 180
    ky = georef.R_EARTH * math.pi / 180
    pts = []
    for name in ("S", "3", "7", "12", "C"):
        x, y = _where(ground, name)
        u, v = gm.latlon_to_px(lat0 + y / ky, lon0 + (x + 30.0) / kx)
        pts.append(dict(control=name, u=float(u * k), v=float((v - gm.header_px) * k)))
    r = client.post(f"/races/{entry}/mapa-rucne/body", json=dict(points=pts), headers={"X-CSRF-Token": csrf(client)})
    d = r.get_json()
    assert d["ok"], d
    assert 25 <= d["shift_m"] <= 35 and d["summary"].startswith("Mapa by se posunula o")
    assert post(client, f"/races/{entry}/mapa-rucne/ulozit").status_code == 302
    assert _md5(course) != before[0] and _md5(maponly) != before[1]           # both maps moved
    assert os.path.exists(course[:-4] + "_puvodni.kmz")
    jobs = con.execute("SELECT COUNT(*) FROM jobs WHERE kind = 'analyse' AND entry_id = ? AND status = 'queued'",
                       (entry,)).fetchone()[0]
    assert jobs == 1
    html = client.get(f"/races/{entry}").get_data(as_text=True)
    assert "Vrátit původní usazení" in html
    # nobody else can move it, nor can they move it back
    post(client, "/logout")
    register(client, "BFM0001")
    assert client.get(f"/races/{entry}/mapa-rucne").status_code == 404
    assert post(client, f"/races/{entry}/mapa-rucne/vratit").status_code == 404
    post(client, "/logout")
    client.post("/login", data=dict(username="BFM0903", password=_password(), csrf_token=csrf(client)))
    assert post(client, f"/races/{entry}/mapa-rucne/vratit").status_code == 302
    assert (_md5(course), _md5(maponly)) == before and not os.path.exists(course[:-4] + "_puvodni.kmz")


def _password():
    import inspect

    import conftest
    return inspect.signature(conftest.register).parameters["password"].default
