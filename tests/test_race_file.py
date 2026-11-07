"""A race saved to a file (.obzavod) and loaded into another runner's app (TODO 49, services/race_file.py). Made-up
maps and runs only, so it runs in the public repo too."""
import io
import json
import re
import zipfile

import pytest
from conftest import FakeOris, csrf
from fitfile import fit_bytes
from PIL import Image
from test_fitload import kmz

from webapp import club
from webapp import db as dbm


def make_app(tmp_path, monkeypatch, name, local=True):
    monkeypatch.setenv("OB_LOCAL", "1" if local else "0")
    monkeypatch.setattr(club, "ENABLED", False)
    from webapp import create_app
    app = create_app(str(tmp_path / name))
    app.config["TESTING"] = True
    app.config["OB"].oris_client = FakeOris()
    app.config["OB"].osm = False
    return app


def con_of(app):
    return dbm.connect(app.config["OB"].db_path)


def form(c, path, files=None, **fields):
    data = dict(fields, csrf_token=csrf(c, "/"))
    data.update(files or {})
    return c.post(path, data=data, content_type="multipart/form-data")


@pytest.fixture
def race(tmp_path, monkeypatch):
    """App A with one race outside ORIS: both maps, a run, official times of the class, a refreshment point,
    a line not to cross and a note to a leg. Returns (app, client, entry id, the bytes of the maps)."""
    app = make_app(tmp_path, monkeypatch, "a")
    c = app.test_client()
    r = form(c, "/races/new", name="Trénink Bělá", date="2026-01-01", place="Bělá", class_name="H18", time="10:00")
    entry_id = int(re.search(r"/races/(\d+)", r.headers["Location"]).group(1))
    maponly = kmz(tmp_path / "maponly.kmz", Image.new("RGB", (400, 300), (255, 255, 255)))
    course = kmz(tmp_path / "course.kmz", Image.new("RGB", (400, 300), (250, 240, 255)))
    fit = fit_bytes([(t, 50.0 + t * 1e-5, 18.0) for t in range(0, 600, 2)])
    r = form(c, f"/races/{entry_id}/files", files=dict(
        maponly=(open(maponly, "rb"), "maponly.kmz"), course=(open(course, "rb"), "course.kmz"),
        fit=(io.BytesIO(fit), "run.fit")))
    assert r.status_code == 302
    con = con_of(app)
    e = con.execute("SELECT class_id, (SELECT event_id FROM classes WHERE id = class_id) AS event_id, activity_id"
                    " FROM entries WHERE id = ?", (entry_id,)).fetchone()
    assert e["activity_id"]
    con.execute("INSERT INTO class_splits (class_id, data) VALUES (?, ?)", (e["class_id"], dbm.dumps(dict(
        control_codes=[31, 32], runners=[dict(name="Klára Kolegyně", regno="BFM0001", club="BFM", place="1",
                                              start_local="10:00:00", time_s=600, status="OK",
                                              cum=[200, 400, 600])]))))
    con.execute("INSERT INTO refreshments (event_id, lat, lon) VALUES (?, 50.001, 18.001)", (e["event_id"],))
    con.execute("INSERT INTO barriers (event_id, line) VALUES (?, ?)",
                (e["event_id"], dbm.dumps([[50.0, 18.0], [50.001, 18.002]])))
    con.execute("UPDATE entries SET own_osm_mode = 'off' WHERE id = ?", (entry_id,))
    con.execute("INSERT INTO leg_notes (entry_id, leg_n, text, lost_contact) VALUES (?, 2, 'ztratil jsem se', 1)",
                (entry_id,))
    con.commit()
    con.close()
    with open(maponly, "rb") as f1, open(course, "rb") as f2:
        return app, c, entry_id, dict(maponly=f1.read(), course=f2.read())


def save(c, entry_id, **ticks):
    r = form(c, f"/races/{entry_id}/soubor", **ticks)
    assert r.status_code == 200 and r.mimetype == "application/zip"
    assert r.headers["Content-Disposition"].endswith('2026-01-01-trenink-bela-h18.obzavod')
    return r.data


def load(c, data, name="zavod.obzavod"):
    r = form(c, "/races/nacist", files=dict(soubor=(io.BytesIO(data), name)))
    assert r.status_code == 302
    return r, c.get(r.headers["Location"]).get_data(as_text=True)


def test_without_ticks_nothing_of_the_runner_goes(race):
    app, c, entry_id, _ = race
    z = zipfile.ZipFile(io.BytesIO(save(c, entry_id)))
    assert sorted(z.namelist()) == ["course.kmz", "maponly.kmz", "obzavod.json"]
    doc = json.loads(z.read("obzavod.json"))
    assert doc["format"] == "obzavod" and doc["version"] == 1 and "mine" not in doc
    assert doc["event"]["name"] == "Trénink Bělá" and doc["class"]["name"] == "H18"
    assert doc["class_splits"]["runners"][0]["regno"] == "BFM0001"
    assert len(doc["refreshments"]) == 1 and len(doc["barriers"]) == 1


def test_loaded_race_has_maps_times_and_points_and_waits_for_a_run(race, tmp_path, monkeypatch):
    _, c, entry_id, maps = race
    data = save(c, entry_id)
    b = make_app(tmp_path, monkeypatch, "b")
    cb = b.test_client()
    r, html = load(cb, data)
    assert "Závod je načtený." in html and "Nahraj k němu svůj běh" in html
    con = con_of(b)
    e = con.execute("SELECT e.*, c.course_file, c.course_source, ev.maponly_file, ev.name, ev.date, ev.id AS event_id"
                    " FROM entries e JOIN classes c ON c.id = e.class_id JOIN events ev ON ev.id = c.event_id").fetchone()
    assert e["name"] == "Trénink Bělá" and e["date"] == "2026-01-01" and e["activity_id"] is None
    assert e["own_osm_mode"] is None and e["official_time_s"] is None      # nothing of the runner who saved it
    conf = b.config["OB"]
    with open(conf.path(e["maponly_file"]), "rb") as f:
        assert f.read() == maps["maponly"]
    with open(conf.path(e["course_file"]), "rb") as f:
        assert f.read() == maps["course"]
    assert e["course_source"] == "kmz"
    assert con.execute("SELECT COUNT(*) FROM refreshments").fetchone()[0] == 1
    assert con.execute("SELECT COUNT(*) FROM barriers").fetchone()[0] == 1
    assert con.execute("SELECT COUNT(*) FROM class_splits").fetchone()[0] == 1
    assert con.execute("SELECT COUNT(*) FROM leg_notes").fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM jobs WHERE kind = 'analyse'").fetchone()[0] == 0
    # the run uploaded afterwards starts the analysis on the loaded maps
    fit = fit_bytes([(t, 50.0 + t * 1e-5, 18.0) for t in range(0, 600, 2)])
    form(cb, f"/races/{e['id']}/files", files=dict(fit=(io.BytesIO(fit), "run.fit")))
    assert con.execute("SELECT COUNT(*) FROM jobs WHERE kind = 'analyse'").fetchone()[0] == 1
    # loading it again adds nothing twice
    _, html = load(cb, data)
    assert "Závod už máš" in html
    assert con.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
    assert con.execute("SELECT COUNT(*) FROM entries").fetchone()[0] == 1
    assert con.execute("SELECT COUNT(*) FROM refreshments").fetchone()[0] == 1
    assert con.execute("SELECT COUNT(*) FROM barriers").fetchone()[0] == 1


def test_with_ticks_the_run_and_settings_go_too(race, tmp_path, monkeypatch):
    _, c, entry_id, _ = race
    data = save(c, entry_id, stopa="1", nastaveni="1")
    z = zipfile.ZipFile(io.BytesIO(data))
    assert "run.fit" in z.namelist()
    b = make_app(tmp_path, monkeypatch, "b")
    _, html = load(b.test_client(), data)
    assert "Běh ze souboru je spárovaný" in html and "Analýza se spustila." in html
    con = con_of(b)
    e = con.execute("SELECT * FROM entries").fetchone()
    assert e["activity_id"] and e["match_confidence"] == "manual"
    assert e["official_time_s"] == 600 and e["own_osm_mode"] == "off"
    note = con.execute("SELECT * FROM leg_notes").fetchone()
    assert note["leg_n"] == 2 and note["text"] == "ztratil jsem se" and note["lost_contact"] == 1


def test_own_result_comes_from_the_times_of_the_class(race, tmp_path, monkeypatch):
    _, c, entry_id, _ = race
    data = save(c, entry_id)
    b = make_app(tmp_path, monkeypatch, "b")
    cb = b.test_client()
    cb.get("/")                                   # the one runner of the app is made on the first visit
    con = con_of(b)
    con.execute("UPDATE users SET oris_regno = 'BFM0001'")
    con.commit()
    load(cb, data)
    e = con.execute("SELECT * FROM entries").fetchone()
    assert e["official_time_s"] == 600 and dbm.loads(e["splits"]) == [200, 400, 600]


def _zip(**members):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, body in members.items():
            z.writestr(name, body)
    return buf.getvalue()


@pytest.mark.parametrize("data, says", [
    (b"this is not a zip at all", "není závod uložený z aplikace"),
    (_zip(**{"doc.kml": "<kml/>"}), "chybí v něm popis závodu"),
    (_zip(**{"obzavod.json": "{nonsense"}), "poškozený"),
    (_zip(**{"obzavod.json": json.dumps(dict(format="obzavod", version=99))}), "novější verzí"),
    (_zip(**{"obzavod.json": json.dumps(dict(format="jiny", version=1))}), "není závod uložený z aplikace"),
    (_zip(**{"obzavod.json": json.dumps(dict(format="obzavod", version=1, event=dict(name="X", date="2026-01-01"),
                                              **{"class": dict(name="H")})), "../evil.py": "x"}), "nepatří"),
    (_zip(**{"obzavod.json": json.dumps(dict(format="obzavod", version=1, event=dict(name="X", date="2026-01-01"),
                                              **{"class": dict(name="H")})), "course.kmz": "no kmz"}),
     "nejde přečíst"),
])
def test_broken_or_foreign_file_says_why_in_czech(tmp_path, monkeypatch, data, says):
    b = make_app(tmp_path, monkeypatch, "b")
    cb = b.test_client()
    _, html = load(cb, data)
    assert says in html
    con = con_of(b)
    assert con.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0     # nothing half loaded


def test_only_in_the_app_on_ones_own_computer(app, client, user):
    assert client.get("/races/nacist").status_code == 404
    assert client.post("/races/1/soubor", data=dict(csrf_token=csrf(client, "/"))).status_code == 404


@pytest.mark.slow
@pytest.mark.needs_data
def test_pohora_saved_without_track_gives_the_same_best_routes(tmp_path, monkeypatch):
    """Pohora analysed in app A, saved without the track, loaded into an empty app B, B's own .fit uploaded:
    the same course, maps and official times, and the same best routes (a few minutes)."""
    import os
    import shutil

    from races import GOLDEN, inputs

    from webapp import seed
    from webapp.worker import load_handlers, run_once

    monkeypatch.setattr(seed, "DEMO", [d for d in seed.DEMO if d["folder"] == "pohora"])
    load_handlers()

    def dem(app, con):
        conf = app.config["OB"]
        os.makedirs(conf.path("dem"), exist_ok=True)
        for (event_id,) in con.execute("SELECT id FROM events"):
            shutil.copyfile(os.path.join(GOLDEN, "pohora", "dem_cache.npz"), conf.path("dem", f"event_{event_id}.npz"))

    def routes(con):
        return [(r["name"], dbm.loads(r["best_route"])) for r in con.execute("SELECT name, best_route FROM legs ORDER BY n")]

    a = make_app(tmp_path, monkeypatch, "a")
    a.config["OB"].dem = "aws"
    ca = a.test_client()
    ca.get("/")
    con_a = con_of(a)
    uid = con_a.execute("SELECT id FROM users").fetchone()["id"]
    entry_a = seed.seed_demo(con_a, a.config["OB"], uid)["pohora"]   # refit as after an upload
    dem(a, con_a)
    run_once(a.config["OB"])
    assert con_a.execute("SELECT has_routes FROM analyses").fetchone()[0] == 1
    data = save_any(ca, entry_a)
    assert "run.fit" not in zipfile.ZipFile(io.BytesIO(data)).namelist()

    b = make_app(tmp_path, monkeypatch, "b")
    b.config["OB"].dem = "aws"
    cb = b.test_client()
    cb.get("/")
    con_b = con_of(b)
    con_b.execute("UPDATE users SET oris_regno = ?", (seed.REGNO,))
    con_b.commit()
    _, html = load(cb, data)
    assert "Závod je načtený." in html
    entry_b = con_b.execute("SELECT id FROM entries").fetchone()["id"]
    ea = con_a.execute("SELECT official_time_s, splits FROM entries").fetchone()
    eb = con_b.execute("SELECT official_time_s, splits FROM entries").fetchone()
    assert tuple(ea) == tuple(eb)              # official times from the times of the class, for B's number
    with open(inputs("pohora")[2], "rb") as f:
        form(cb, f"/races/{entry_b}/files", files=dict(fit=(io.BytesIO(f.read()), "run.fit")))
    dem(b, con_b)
    run_once(b.config["OB"])
    failed = [dict(j) for j in con_b.execute("SELECT kind, error FROM jobs WHERE status != 'done'")]
    assert not failed, failed
    assert routes(con_b) == routes(con_a) and len(routes(con_a)) > 5


def save_any(c, entry_id, **ticks):
    r = form(c, f"/races/{entry_id}/soubor", **ticks)
    assert r.status_code == 200
    return r.data
