"""The page "Ztratil jsem se u kontroly" (webapp/views/lost.py): the scenes are prepared by a short job when the page
finds them missing or stale, the advice comes back as JSON with Czech sentences, the description of a control is
kept by hand and changes nothing that is computed."""
import json
import os

import numpy as np
from conftest import csrf, post, register
from test_recompute import _fake_refit, _scripts
from test_web_races import con_of, work

from oroute import lost
from webapp import db as dbm
from webapp.seed import seed_demo
from webapp.services import personal, runner

P = (49.6, 18.3)        # where the made-up analysis of _scripts puts every control


def send(client, url, body):
    return client.post(url, json=body, headers={"X-CSRF-Token": csrf(client)})


def _scene():
    """A scene of 300 x 300 cells of 1 m with the control in the middle at P and a path all across 60 m north."""
    n = 300
    meta = dict(shape=[n, n], s=1, cell=1.0, origin=list(P), A=[[0.0, -11.12], [7.2, 0.0], [150.0, 150.0]],
                ctrl=[150.0, 150.0], prev=[150.0, 290.0], points=[])
    arrays = {k: np.zeros((n, n), bool) for k in lost.LINES + ("imp",)}
    arrays["path"][90, :] = True
    return meta, arrays


def _with_lost(log, fail=None):
    """_scripts with oroute.lost: writes the scenes of the two controls with the stamp it was given."""
    base = _scripts(log)

    def run(*cmd, on_line=None):
        if cmd[:2] == ("-m", "oroute.lost"):
            log.append(("lost", "--analysis" in cmd))
            if fail:
                raise runner.AnalysisError(fail)
            out = cmd[3]
            stamp = json.loads(cmd[cmd.index("--stamp") + 1])
            lost.save(os.path.join(out, "lost.json"), os.path.join(out, "lost.npz"), {1: _scene(), 2: _scene()},
                      stamp=stamp)
            return
        return base(*cmd, on_line=on_line)
    return run


def _ready(app, client, user, monkeypatch, fail=None):
    con, conf = con_of(app), app.config["OB"]
    entry = seed_demo(con, conf, user)["pohora"]
    con.execute("DELETE FROM jobs WHERE entry_id IS NOT ?", (entry,))
    con.commit()
    log = []
    monkeypatch.setattr(runner, "_run", _with_lost(log, fail))
    monkeypatch.setattr(personal, "refit", _fake_refit(log, [True]))
    work(app)                                   # the analysis
    return con, entry, log


def test_the_page_prepares_the_scenes_once_then_advises(app, client, user, monkeypatch):
    con, entry, log = _ready(app, client, user, monkeypatch)
    html = client.get(f"/races/{entry}/ztraceny").get_data(as_text=True)
    assert "Připravuju mapu kolem kontrol" in html
    assert con.execute("SELECT COUNT(*) FROM jobs WHERE kind = 'lost_scene' AND status = 'queued'").fetchone()[0] == 1
    client.get(f"/races/{entry}/ztraceny")                  # asked again: still one job
    assert con.execute("SELECT COUNT(*) FROM jobs WHERE kind = 'lost_scene'").fetchone()[0] == 1
    assert client.get(f"/races/{entry}/ztraceny/stav.json").get_json()["state"] == "preparing"
    work(app)
    assert ("lost", True) in log                            # with the analysis of the entry
    html = client.get(f"/races/{entry}/ztraceny").get_data(as_text=True)
    assert 'id="z-mapa"' in html and 'data-k="1"' in html and 'data-k="2"' in html
    assert "Jen kontrola a okolí" in html and "Kde jsem asi byl" in html
    assert "Po závodě: kde jsem se ztratil" in html
    assert client.get(f"/races/{entry}/ztraceny/stav.json").get_json()["state"] == "ready"
    # the runner 60 m south of the control, unsure by 25 m: the path 120 m north of them
    r = send(client, f"/races/{entry}/ztraceny/rada", dict(k=1, lat=P[0] - 60 / 111200, lon=P[1], r=25))
    assert r.status_code == 200
    a = r.get_json()
    h = a["helpers"][a["pick"]]
    assert h["kind"] == "path" and h["sure"] and abs(h["dist"] - 120) < 3 and abs(h["az"]) < 2
    assert a["sentences"][0].startswith("Neměl jsi hádat směr ke kontrole. Nejdřív jsi měl dojít na sever k cestě "
                                        "(asi 120 m")
    assert a["names"][0]["text"].startswith("cesta: od tebe 120 m na azimut 0°")
    # only the control and around it
    a = send(client, f"/races/{entry}/ztraceny/rada", dict(k=2, r=50)).get_json()
    assert a["no_runner"] and a["sentences"][0].startswith("Když jsi nevěděl, kde u kontroly jsi: na sever byla do")
    # nothing new is computed for the advice
    assert con.execute("SELECT COUNT(*) FROM jobs WHERE kind != 'lost_scene' AND status = 'queued'").fetchone()[0] == 0


def test_bad_requests_and_other_runners(app, client, user, monkeypatch):
    con, entry, log = _ready(app, client, user, monkeypatch)
    client.get(f"/races/{entry}/ztraceny")
    work(app)
    url = f"/races/{entry}/ztraceny/rada"
    assert send(client, url, dict(k=9, r=50)).status_code == 400                 # no such control
    assert send(client, url, dict(k=1, r=500)).status_code == 400                # circle too wide
    assert send(client, url, dict(k=1, lat=49.6, r=50)).status_code == 400       # lat without lon
    assert send(client, url, dict(r=50)).status_code == 400
    assert client.get(f"/races/{entry}/ztraceny/zpetne").status_code == 400
    assert client.get(f"/races/{entry + 999}/ztraceny").status_code == 404
    post(client, "/logout")
    register(client, "BFM0001")
    assert client.get(f"/races/{entry}/ztraceny").status_code == 404
    assert send(client, url, dict(k=1, r=50)).status_code == 404


def test_a_map_placed_again_makes_the_scenes_stale(app, client, user, monkeypatch):
    con, entry, log = _ready(app, client, user, monkeypatch)
    client.get(f"/races/{entry}/ztraceny")
    work(app)
    assert client.get(f"/races/{entry}/ztraceny/stav.json").get_json()["state"] == "ready"
    e = con.execute("SELECT ev.maponly_file FROM entries e JOIN classes c ON c.id = e.class_id JOIN events ev"
                    " ON ev.id = c.event_id WHERE e.id = ?", (entry,)).fetchone()
    path = app.config["OB"].path(e["maponly_file"])
    st = os.stat(path)
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
    assert client.get(f"/races/{entry}/ztraceny/stav.json").get_json()["state"] == "preparing"
    assert send(client, f"/races/{entry}/ztraceny/rada", dict(k=1, r=50)).status_code == 409


def test_a_failed_scene_is_not_tried_again_by_itself(app, client, user, monkeypatch):
    con, entry, log = _ready(app, client, user, monkeypatch, fail="Mapa se nedala přečíst.")
    client.get(f"/races/{entry}/ztraceny")
    work(app)
    html = client.get(f"/races/{entry}/ztraceny").get_data(as_text=True)
    assert "nepodařilo připravit" in html and "Mapa se nedala přečíst." in html
    assert con.execute("SELECT COUNT(*) FROM jobs WHERE kind = 'lost_scene' AND status = 'queued'").fetchone()[0] == 0
    r = client.post(f"/races/{entry}/ztraceny/pripravit", data=dict(csrf_token=csrf(client)))
    assert r.status_code == 302
    assert con.execute("SELECT COUNT(*) FROM jobs WHERE kind = 'lost_scene' AND status = 'queued'").fetchone()[0] == 1


def test_the_description_is_kept_and_changes_nothing_computed(app, client, user, monkeypatch):
    con, entry, log = _ready(app, client, user, monkeypatch)
    client.get(f"/races/{entry}/ztraceny")
    work(app)
    r = send(client, f"/races/{entry}/ztraceny/popis", dict(k=1, text="  kupka,   severní úpatí "))
    assert r.get_json() == dict(k=1, desc="kupka, severní úpatí")
    assert con.execute("SELECT COUNT(*) FROM jobs WHERE status = 'queued'").fetchone()[0] == 0     # no refit
    a = send(client, f"/races/{entry}/ztraceny/rada", dict(k=1, r=50)).get_json()
    assert a["sentences"][-1] == "Podle popisu jsi hledal: kupka, severní úpatí."
    leg1 = next(l for l in client.get(f"/races/{entry}/legs.json").get_json()["legs"] if l["n"] == 1)
    assert leg1["note"]["control_desc"] == "kupka, severní úpatí"
    # a note of the leg without the description keeps it; with it, changes it
    send(client, f"/races/{entry}/legs/1/note", dict(text="ahoj"))
    assert con.execute("SELECT control_desc FROM leg_notes WHERE entry_id = ? AND leg_n = 1", (entry,)).fetchone()[0] \
        == "kupka, severní úpatí"
    send(client, f"/races/{entry}/legs/1/note", dict(text="ahoj", control_desc=""))
    assert con.execute("SELECT control_desc FROM leg_notes WHERE entry_id = ? AND leg_n = 1", (entry,)).fetchone()[0] \
        is None
    assert con.execute("SELECT COUNT(*) FROM jobs WHERE kind = 'refit_model' AND status = 'queued'").fetchone()[0] == 0
    assert send(client, f"/races/{entry}/ztraceny/popis", dict(k="x")).status_code == 400


def test_looking_back_needs_the_analysis_and_answers(app, client, user, monkeypatch):
    con, entry, log = _ready(app, client, user, monkeypatch)
    client.get(f"/races/{entry}/ztraceny")
    work(app)
    d = client.get(f"/races/{entry}/ztraceny/zpetne?k=1").get_json()
    assert d["moments"] == [] and len(d["track"]) == 2       # the made-up track has two points on the leg


def test_the_race_page_links_to_it(app, client, user, monkeypatch):
    con, entry, log = _ready(app, client, user, monkeypatch)
    html = client.get(f"/races/{entry}").get_data(as_text=True)
    assert f'href="/races/{entry}/ztraceny"' in html and "Ztratil jsem se u kontroly" in html
    assert f'ztraceny: "/races/{entry}/ztraceny"' in html


def test_it_is_a_look_back_after_the_race_only(app, client, user, monkeypatch):
    """No aid during a race (a phone with its position is not allowed there): the page has nothing for the forest,
    and tapping where one was still gives the advice."""
    con, entry, log = _ready(app, client, user, monkeypatch)
    client.get(f"/races/{entry}/ztraceny")
    work(app)
    html = client.get(f"/races/{entry}/ztraceny").get_data(as_text=True)
    js = client.get("/ob-static/lost.js").get_data(as_text=True)
    assert "init()" in js
    help_html = client.get("/jak-na-to").get_data(as_text=True)
    for text in (html, js, help_html):
        for gone in ("geolocation", "Teď v lese", "Moje poloha", "z-gps", "na trénink", "Do terénu", "do terénu"):
            assert gone not in text, gone
    a = send(client, f"/races/{entry}/ztraceny/rada", dict(k=1, lat=P[0] - 60 / 111200, lon=P[1], r=25)).get_json()
    assert a["pick"] is not None and a["sentences"]
    # without a circle the one of the map: 50 m in the forest
    assert send(client, f"/races/{entry}/ztraceny/rada", dict(k=2)).get_json()["r"] == 50


def test_no_look_back_before_the_race(app, client, user, monkeypatch):
    con, entry, log = _ready(app, client, user, monkeypatch)
    ev = con.execute("SELECT c.event_id FROM entries e JOIN classes c ON c.id = e.class_id WHERE e.id = ?",
                     (entry,)).fetchone()[0]
    con.execute("UPDATE events SET date = date('now', '+3 days') WHERE id = ?", (ev,))
    con.execute("UPDATE entries SET activity_id = NULL WHERE id = ?", (entry,))
    con.commit()
    html = client.get(f"/races/{entry}").get_data(as_text=True)
    assert f'href="/races/{entry}/ztraceny"' not in html and 'ztraceny: ""' in html
    assert "bude po závodě" in html
    page = client.get(f"/races/{entry}/ztraceny").get_data(as_text=True)
    assert "je po závodě" in page and 'id="z-mapa"' not in page
    assert con.execute("SELECT COUNT(*) FROM jobs WHERE kind = 'lost_scene'").fetchone()[0] == 0


def test_old_database_gets_the_column_of_the_description(tmp_path):
    path = str(tmp_path / "app.db")
    con = dbm.connect(path)
    con.executescript("CREATE TABLE leg_notes (entry_id INTEGER NOT NULL, leg_n INTEGER NOT NULL, planned TEXT,"
                      " deliberate_stop INTEGER NOT NULL DEFAULT 0, lost_contact INTEGER NOT NULL DEFAULT 0, green TEXT,"
                      " fatigue INTEGER, text TEXT, updated_at TEXT NOT NULL DEFAULT (datetime('now')),"
                      " PRIMARY KEY (entry_id, leg_n));"
                      "INSERT INTO leg_notes (entry_id, leg_n, text) VALUES (1, 1, 'x');")
    con.commit()
    dbm.init(path)
    assert tuple(con.execute("SELECT text, control_desc FROM leg_notes").fetchone()) == ("x", None)
