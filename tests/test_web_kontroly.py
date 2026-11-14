"""Doplnit kontroly (views/coursefix.py): the points to click are the controls of ORIS, not the circles found; the
course saved by hand is used by the analysis until a new map with the course comes; the race page says when the
course read from the map does not agree with ORIS."""
import json
import math
import os
import re
import shutil

import pytest
from conftest import csrf, post
from test_web_races import con_of

from oroute import georef
from oroute.course import save_course
from webapp.seed import seed_demo
from webapp.services import mapfix, runner, storage


def _setup(app, user):
    con, conf = con_of(app), app.config["OB"]
    entry = seed_demo(con, conf, user)["pohora"]
    con.execute("DELETE FROM jobs")
    con.commit()
    e = con.execute("SELECT e.*, c.course_file, c.course_source, c.event_id, c.id AS class_id, ev.maponly_file"
                    " FROM entries e JOIN classes c ON c.id = e.class_id JOIN events ev ON ev.id = c.event_id"
                    " WHERE e.id = ?", (entry,)).fetchone()
    return con, conf, entry, e


def _on_map(app, conf, e):
    """(ground_course, function name -> preview pixels where the watch was at that punch, GeoMap, scale)."""
    from webapp.views.photo import _ground, _where
    with app.test_request_context():
        ground, lat0, lon0, _t = _ground(dict(e))
    _p, _size, k, gm = mapfix.preview(conf, e["course_file"])
    kx = georef.R_EARTH * math.cos(math.radians(lat0)) * math.pi / 180
    ky = georef.R_EARTH * math.pi / 180

    def at(name):
        x, y = _where(ground, name)
        u, v = gm.latlon_to_px(lat0 + y / ky, lon0 + x / kx)
        return float(u * k), float((v - gm.header_px) * k)
    return ground, at, gm, k


def _analysed(con, conf, entry, gm, k, at, names, summary=None):
    """An analysis whose course has only the controls `names` (as if the others were not found on the map)."""
    out = os.path.join("races", f"entry_{entry}")
    os.makedirs(conf.path(out), exist_ok=True)
    full = lambda n: (at(n)[0] / k, at(n)[1] / k + gm.header_px)
    save_course(conf.path(out, "course.json"), gm, {"start": full("S"), "controls": [full(n) for n in names],
                                                    "finish": full("C")})
    con.execute("INSERT INTO analyses (entry_id, has_routes, total_time_s, summary, out_dir) VALUES (?, 0, 3022, ?, ?)",
                (entry, json.dumps(summary or {}), out))
    con.commit()


def test_the_points_are_the_controls_of_oris_and_the_course_is_kept(app, client, user, monkeypatch):
    con, conf, entry, e = _setup(app, user)
    ground, at, gm, k = _on_map(app, conf, e)
    n = len(ground["controls"])
    assert n >= 10
    found = [str(i) for i in range(1, n + 1) if i not in (3, 7, 9)]          # three circles not found on the map
    _analysed(con, conf, entry, gm, k, at, found)
    html = client.get(f"/races/{entry}/kontroly").get_data(as_text=True)
    assert f"Trať má podle ORIS <b>{n} kontrol</b>" in html and f"Na mapě jsem jich našel {n - 3}" in html
    names = json.loads(re.search(r"names: (\[.*?\]\]),", html).group(1))
    assert [m for m, _ok in names] == ["S"] + [str(i) for i in range(1, n + 1)] + ["C"]
    points = json.loads(re.search(r"points: (\[.*?\]),\n", html).group(1))
    assert sorted(p[0] for p in points) == sorted(["S", "C"] + found)        # each circle has the number of its punch
    assert all(math.hypot(p[1] - at(p[0])[0], p[2] - at(p[0])[1]) < 1 for p in points)
    assert client.get(f"/races/{entry}/kontroly.jpg").status_code == 200
    # placing the map by hand also offers every control of ORIS, not the circles found
    html = client.get(f"/races/{entry}/mapa-rucne").get_data(as_text=True)
    assert len(json.loads(re.search(r"names: (\[.*?\]\]),", html).group(1))) == n + 2
    # the missing three clicked where they are, one of them on another control first
    pts = [dict(control=m, u=u, v=v) for m, u, v in points] + [dict(control=m, u=at(m)[0], v=at(m)[1])
                                                                 for m in ("3", "7")]
    pts.append(dict(control="9", u=at("1")[0], v=at("1")[1]))
    hdr = {"X-CSRF-Token": csrf(client)}
    d = client.post(f"/races/{entry}/kontroly/body", json=dict(points=pts), headers=hdr).get_json()
    assert d["ok"] and d["deviation"]["9"] > 40 and any("Bod 9" in p for p in d["problems"])
    pts[-1] = dict(control="9", u=at("9")[0], v=at("9")[1])
    d = client.post(f"/races/{entry}/kontroly/body", json=dict(points=pts), headers=hdr).get_json()
    assert d["ok"] and not d["problems"] and max(d["deviation"].values()) < 2 and d["track"]
    assert post(client, f"/races/{entry}/kontroly/ulozit").status_code == 302
    path = conf.path(storage.course_json(e["course_file"]))
    with open(path, encoding="utf-8") as f:
        saved = json.load(f)
    assert saved["by_hand"] and len(saved["controls"]) == n
    assert con.execute("SELECT COUNT(*) FROM jobs WHERE kind = 'analyse' AND entry_id = ?", (entry,)).fetchone()[0] == 1
    assert "jsou označené ručně" in client.get(f"/races/{entry}").get_data(as_text=True)

    # the analysis takes it instead of reading the map, also when only the routes are found again
    calls = []

    class Done(Exception):
        pass

    def run(*cmd, **kw):
        calls.append(cmd)
        raise Done
    monkeypatch.setattr(runner, "_run", run)
    info = runner.entry_info(con, entry)
    with pytest.raises(Done):
        runner._analyse_in(con, conf, info, os.path.join("races", "x"), True, lambda t: None, None, None, None)
    cmd = calls[-1]
    assert cmd[0] == "analyze.py" and "--course" in cmd
    assert cmd[cmd.index("--oris-controls") + 1] == str(n)

    # a new map with the course drops it
    tmp = storage.incoming(conf, ".kmz")[1]
    shutil.copyfile(conf.path(e["course_file"]), tmp)
    storage.save_map(conf, tmp, e["event_id"], e["class_id"])
    assert not os.path.exists(path)


def test_race_page_says_when_the_course_does_not_agree_with_oris(app, client, user):
    con, conf, entry, e = _setup(app, user)
    _ground, at, gm, k = _on_map(app, conf, e)
    _analysed(con, conf, entry, gm, k, at, ["1", "2"],
              summary=dict(course_check=dict(found=13, added=0, removed=0, expected=16, source="map")))
    html = client.get(f"/races/{entry}").get_data(as_text=True)
    assert "Kontrol na mapě: 13, v ORIS: 16" in html and f"/races/{entry}/kontroly" in html
    con.execute("UPDATE analyses SET summary = ? WHERE entry_id = ?",
                (json.dumps(dict(course_check=dict(found=14, added=2, removed=0, expected=16, source="map"))), entry))
    con.commit()
    html = client.get(f"/races/{entry}").get_data(as_text=True)
    assert "Kontrol na mapě" not in html and "2 jsem dohledal podle místa" in html
    # all fine, or a course given by hand: nothing said
    for check in (dict(found=16, added=0, removed=0, expected=16, source="map"),
                  dict(found=15, added=0, removed=0, expected=16, source="manual"), None):
        con.execute("UPDATE analyses SET summary = ? WHERE entry_id = ?", (json.dumps(dict(course_check=check)), entry))
        con.commit()
        html = client.get(f"/races/{entry}").get_data(as_text=True)
        assert "Kontrol na mapě" not in html and "dohledal" not in html


def test_without_oris_the_number_of_controls_is_given(app, client, user):
    # a race added by hand (Azymut, not in ORIS): as many points as asked for
    con, conf = con_of(app), app.config["OB"]
    entry = seed_demo(con, conf, user)["azymut-e4"]
    html = client.get(f"/races/{entry}/kontroly?n=5").get_data(as_text=True)
    names = json.loads(re.search(r"names: (\[.*?\]\]),", html).group(1))
    assert [m for m, _ok in names] == ["S", "1", "2", "3", "4", "5", "C"] and 'name="n"' in html
    assert client.get(f"/races/{entry}/kontroly?n=500").status_code == 200
