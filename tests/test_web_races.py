"""Races in the web app without running the analysis: ORIS sync, manual race, uploads, matching, ownership."""
import datetime as dt
import io
import json
import os

import pytest
from conftest import FakeOris, clear_jobs, csrf, post, register
from races import inputs

from oroute.kmzmap import GeoMap
from webapp import db as dbm
from webapp.seed import seed_demo
from webapp.services import jobs, personal, runner, storage, sync_oris
from webapp.worker import load_handlers, run_once


def con_of(app):
    return dbm.connect(app.config["OB"].db_path)


def work(app):
    load_handlers()
    return run_once(app.config["OB"])


def synced(app, client, user):
    con = con_of(app)
    msg = sync_oris.sync_user(con, app.config["OB"], user, client=FakeOris(), today=dt.date(2026, 10, 6), pause=0)
    return con, msg


def test_sync_oris(app, client, user):
    con, msg = synced(app, client, user)
    assert "2 závodů (2 nových)" in msg
    rows = {r["oris_id"]: r for r in con.execute(
        "SELECT ev.oris_id, ev.name, ev.livelox_id, c.name AS cls, c.controls, e.official_time_s, e.start_local, e.splits"
        " FROM entries e JOIN classes c ON c.id = e.class_id JOIN events ev ON ev.id = c.event_id")}
    assert rows[8989]["cls"] == "H16C" and rows[8989]["official_time_s"] == 3022 and rows[8989]["start_local"] == "13:18:00"
    assert rows[9827]["livelox_id"] == "182468" and rows[9827]["controls"] == 19
    assert dbm.loads(rows[9827]["splits"])[-1] == 4818
    # a second sync adds nothing
    assert "(0 nových)" in sync_oris.sync_user(con, app.config["OB"], user, client=FakeOris(), pause=0,
                                               today=dt.date(2026, 10, 6))
    html = client.get("/").get_data(as_text=True)
    assert "Mistrovství oblasti na dlouhé trati" in html and "80:18" in html
    assert "https://www.livelox.com/Events/Show/182468" in html


def test_unknown_regno_fails_with_a_message(app):
    con = con_of(app)
    user = con.execute("INSERT INTO users (username, password_hash, oris_regno) VALUES ('XXX0000', 'x', 'XXX0000')"
                       ).lastrowid
    con.commit()
    try:
        sync_oris.sync_user(con, app.config["OB"], user, client=FakeOris(), pause=0)
        assert False
    except ValueError as e:
        assert "XXX0000 v ORIS není" in str(e)


def test_manual_race_and_fit_upload_are_matched(app, client, user):
    r = post(client, "/races/new", name="Azymut Cup 2026 - Day 5", date="2026-08-14", class_name="O3", time="76:57")
    assert r.status_code == 302
    page = r.headers["Location"]
    assert "chybí aktivita" in client.get("/").get_data(as_text=True)
    with open(inputs("azymut-e5")[2], "rb") as f:
        r = client.post("/upload", data=dict(csrf_token=csrf(client), files=(io.BytesIO(f.read()), "run.fit")),
                        content_type="multipart/form-data")
    assert r.status_code == 302
    assert work(app) == 1  # the import; no analysis yet, the map with the course is missing
    con = con_of(app)
    job = con.execute("SELECT * FROM jobs").fetchone()
    assert job["status"] == "done", job["error"]
    e = con.execute("SELECT * FROM entries").fetchone()
    assert e["activity_id"] and e["match_confidence"] == "high"
    html = client.get(page).get_data(as_text=True)
    assert "shoda jistá" in html and "77:02" in html
    # uploading the same file again does not duplicate it
    with open(inputs("azymut-e5")[2], "rb") as f:
        client.post("/upload", data=dict(csrf_token=csrf(client), files=(io.BytesIO(f.read()), "again.fit")),
                    content_type="multipart/form-data")
    work(app)
    assert con.execute("SELECT COUNT(*) FROM activities").fetchone()[0] == 1


def test_upload_refuses_other_files(app, client, user):
    r = client.post("/upload", data=dict(csrf_token=csrf(client), files=(io.BytesIO(b"x"), "photo.jpg")),
                    content_type="multipart/form-data")
    assert "jen .fit nebo .zip" in r.get_data(as_text=True)
    client.post("/upload", data=dict(csrf_token=csrf(client), files=(io.BytesIO(b"not a fit"), "bad.fit")),
                content_type="multipart/form-data")
    work(app)
    job = con_of(app).execute("SELECT * FROM jobs").fetchone()
    assert job["status"] == "failed" and "není aktivita" in job["error"]
    client.post("/upload", data=dict(csrf_token=csrf(client), files=(io.BytesIO(b"not a zip"), "export.zip")),
                content_type="multipart/form-data")
    work(app)
    job = con_of(app).execute("SELECT * FROM jobs ORDER BY id DESC").fetchone()
    assert job["status"] == "failed" and job["error"].startswith("Soubor není zip")


def upload_kmz(client, page, kind, path=None, data=None):
    if data is None:
        with open(path, "rb") as f:
            data = f.read()
    return client.post(page + "/map", data=dict(csrf_token=csrf(client), kind=kind, kmz=(io.BytesIO(data), "map.kmz")),
                       content_type="multipart/form-data", follow_redirects=True)


def test_map_upload_is_shared_by_the_event(app, client, user):
    con, _ = synced(app, client, user)
    mine = con.execute("SELECT e.id FROM entries e JOIN classes c ON c.id = e.class_id JOIN events ev"
                       " ON ev.id = c.event_id WHERE ev.oris_id = 8989").fetchone()["id"]
    page = f"/races/{mine}"
    assert "není KMZ s mapou" in upload_kmz(client, page, "maponly", data=b"nothing").get_data(as_text=True)
    course, maponly, _ = inputs("pohora")
    assert "uložená pro všechny" in upload_kmz(client, page, "maponly", maponly).get_data(as_text=True)
    assert "uložená pro kategorii H16C" in upload_kmz(client, page, "course", course).get_data(as_text=True)
    assert client.get(page + "/map/maponly.img").status_code == 200
    # no activity yet, so nothing was queued
    assert con.execute("SELECT COUNT(*) FROM jobs WHERE kind = 'analyse'").fetchone()[0] == 0

    # a clubmate in another class of the same event gets the map without course, not the course
    post(client, "/logout")
    register(client, "BFM0001")
    clear_jobs(app)
    other = con.execute("SELECT id FROM users WHERE username = 'BFM0001'").fetchone()["id"]
    event = con.execute("SELECT id FROM events WHERE oris_id = 8989").fetchone()["id"]
    # the other class of the race, kept by the sync with the one entered
    cls = con.execute("SELECT id FROM classes WHERE event_id = ? AND name = 'D21C'", (event,)).fetchone()[0]
    theirs = con.execute("INSERT INTO entries (user_id, class_id) VALUES (?, ?)", (other, cls)).lastrowid
    con.commit()
    html = client.get(f"/races/{theirs}").get_data(as_text=True)
    assert html.count("nahraná") == 1 and html.count(">chybí<") == 1
    # and cannot open somebody else's race
    assert client.get(page).status_code == 404
    assert client.get(page + "/data.json").status_code == 404
    assert client.get(page + "/map/course.img").status_code == 404
    assert upload_kmz(client, page, "course", course).status_code == 404


def test_map_is_read_once_and_kept_by_the_browser(app, client, user, monkeypatch):
    con, _ = synced(app, client, user)
    mine = con.execute("SELECT e.id FROM entries e JOIN classes c ON c.id = e.class_id JOIN events ev"
                       " ON ev.id = c.event_id WHERE ev.oris_id = 8989").fetchone()["id"]
    page = f"/races/{mine}"
    upload_kmz(client, page, "maponly", inputs("pohora")[1])
    conf = app.config["OB"]
    rel = con.execute("SELECT maponly_file FROM events WHERE oris_id = 8989").fetchone()[0]
    meta = storage.map_meta(conf, rel)
    assert len(meta["corners"]) == 3 and os.path.exists(conf.path(rel) + ".json")
    # where the map lies was worked out at the upload: a page view does not decode the picture again
    monkeypatch.setattr(GeoMap, "from_kmz", classmethod(lambda cls, path: 1 / 0))
    assert storage.map_meta(conf, rel) == meta
    # the address the page uses carries the stamp of the upload, so the picture may be kept for good
    r = client.get(f"{page}/map/maponly.img?v={meta['stamp'][1]}")
    assert r.status_code == 200 and r.headers["Cache-Control"] == "private, max-age=31536000, immutable"
    assert client.get(f"{page}/map/maponly.img").headers["Cache-Control"] == "private, max-age=3600"
    # the race page loads itself again only while a job of the race is waiting or running
    assert "data-obnovit" not in client.get(page).get_data(as_text=True)
    jobs.enqueue(con, "analyse", user_id=user, entry_id=mine, payload=dict(refit=True))
    assert "data-obnovit" in client.get(page).get_data(as_text=True)


def _fake_scripts(con, entry_id, log):
    """Stand-in for runner._run: writes what analyze.py and bestroute.py leave behind (three legs) and notes
    in `log` what ran and what the database held for the entry at that moment."""
    route = dict(time=60.0, dist=200.0, climb=5.0, mix={})

    def stored():
        row = con.execute("SELECT has_routes FROM analyses WHERE entry_id = ?", (entry_id,)).fetchone()
        return None if row is None else row["has_routes"]

    def run(*cmd, on_line=None):
        if cmd[:2] == ("-m", "oroute.hatch"):
            with open(cmd[3], "w") as f:
                json.dump(dict(areas=[]), f)
        elif cmd[:2] == ("-m", "oroute.relocate"):
            with open(cmd[4], "w") as f:
                json.dump(dict(controls=[]), f)
        elif cmd[0] == "analyze.py":
            log.append(("analyze", "--no-images" in cmd, stored()))
            out = cmd[3]
            p = dict(lat=49.6, lon=18.3)
            with open(os.path.join(out, "course.json"), "w") as f:
                json.dump(dict(start=p, controls=[p, p], finish=p), f)
            legs = [dict(leg=k, name=n, time=70.0, est_loss=5.0, stops=[], a=k - 1, b=k, straight=180.0, run=210.0,
                         climb=5.0, stop_time=0.0, flags=[]) for k, n in enumerate(("S-1", "1-2", "2-F"), 1)]
            with open(os.path.join(out, "analysis.json"), "w") as f:
                json.dump(dict(start="2026-03-28T09:00:00+00:00", total_time=210.0, est_loss=15.0, vref=3.0, rref=1.1,
                               offset_m=[0, 0], weak_order=[], official=None, course=[p] * 4, punch=[0, 1, 2, 3],
                               track=dict(t=[0, 70, 140, 210], lat=[49.6] * 4, lon=[18.3] * 4, speed=[3.0] * 4),
                               legs=legs), f)
        elif "--samples-only" in cmd:
            log.append(("samples", "--no-images" in cmd, stored()))
            open(os.path.join(cmd[4], "leg_samples.npz"), "wb").close()
            on_line("reading terrain ...")
        else:
            log.append(("routes", "--no-images" in cmd, stored()))
            for line in ("building grid ... (0, 0, 9, 9)", "S-1: actual 1:10  your line", "   text of the leg",
                         "1-2: actual 1:10  your line"):
                on_line(line)
            log.append(("message", con.execute("SELECT message FROM jobs WHERE status = 'running'").fetchone()[0]))
            with open(os.path.join(cmd[4], "best.json"), "w") as f:
                json.dump(dict(dem="aws", barriers=None, legs=[
                    dict(leg=k, best=route, yours=route, straight=route, route=[[49.6, 18.3], [49.6, 18.3]],
                         text_cs="rovně", text_en="straight") for k in (1, 2, 3)]), f)
    return run


def test_new_race_shows_the_track_first_and_finds_the_routes_once(app, client, user, monkeypatch):
    """One job of a new race: analyze.py, then the track is on the page; what the speed model learns from
    the race, the refit of the model, and only then the routes, once, with that model."""
    con, conf = con_of(app), app.config["OB"]
    entry = seed_demo(con, conf, user)["petrvald"]
    con.execute("DELETE FROM jobs WHERE entry_id IS NOT ?", (entry,))
    con.commit()
    page = f"/races/{entry}"
    state = client.get(f"/jobs.json?entry={entry}").get_json()
    assert state["analysis"] == "" and state["progress"] == "Analýza závodu: čeká ve frontě."
    html = client.get(page).get_data(as_text=True)
    assert 'id="ob-prubeh"' in html and 'data-analyza=""' in html and "data-obnovit" in html

    log = []
    monkeypatch.setattr(runner, "_run", _fake_scripts(con, entry, log))
    monkeypatch.setattr(personal, "refit", lambda con, conf, uid, fresh=None: log.append(("refit", fresh)) or (None, True))
    work(app)
    job = con.execute("SELECT * FROM jobs").fetchall()
    assert len(job) == 1 and job[0]["status"] == "done", [dict(j) for j in job]   # no second job for the routes
    assert job[0]["message"] == "Analýza hotová, osobní model přepočítán."
    rel = os.path.join("races", f"entry_{entry}")
    assert log == [("analyze", True, None),            # nothing stored yet
                   ("samples", True, 0),               # the track is stored before anything about the routes
                   ("refit", (entry, rel)),            # the race joins the model before its routes are found
                   ("routes", True, 0),
                   ("message", "hledám nejlepší postupy: 2 z 3 úseků")]
    state = client.get(f"/jobs.json?entry={entry}").get_json()
    assert state["analysis"] and state["progress"] == "" and state["active"] == 0 and state["running"] == []
    html = client.get(page).get_data(as_text=True)
    assert 'id="ob-prubeh"' not in html and "data-obnovit" not in html and f'data-analyza="{state["analysis"]}"' in html
    assert "Únava 1–3 jen popisuje" in html            # the panel says which fatigue values count
    assert con.execute("SELECT has_routes FROM analyses WHERE entry_id = ?", (entry,)).fetchone()[0] == 1

    # the same race again: the page keeps the routes it has until the new ones are found
    del log[:]
    post(client, page + "/reanalyse")
    work(app)
    assert [x[:3] for x in log if x[0] in ("analyze", "samples", "routes")] == \
        [("analyze", True, 1), ("samples", True, 1), ("routes", True, 1)]
    # somebody else's race tells nothing
    post(client, "/logout")
    register(client, "BFM0001")
    assert "analysis" not in client.get(f"/jobs.json?entry={entry}").get_json()


def test_garmin_export_keeps_only_runs_paired_with_races(app, client, user):
    """The whole export is used for pairing (and the hill model), then only the paired runs stay."""
    import zipfile
    con, _ = synced(app, client, user)
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as z:
        for folder in ("pohora", "azymut-e5", "azymut-e4"):      # one race of this runner, two other runs
            with open(inputs(folder)[2], "rb") as f:
                z.writestr(f"{folder}.fit", f.read())
    export = io.BytesIO()
    with zipfile.ZipFile(export, "w") as z:
        z.writestr("DI_CONNECT/DI-Connect-Uploaded-Files/UploadedFiles_0-_Part1.zip", inner.getvalue())
        z.writestr("DI_CONNECT/DI-Connect-User/user_profile.json", "{}")
    r = client.post("/upload", data=dict(csrf_token=csrf(client), files=(io.BytesIO(export.getvalue()), "export.zip")),
                    content_type="multipart/form-data")
    assert r.status_code == 302
    work(app)
    job = con.execute("SELECT * FROM jobs WHERE kind = 'import_upload'").fetchone()
    assert job["status"] == "done", job["error"]
    assert "běhů 3" in job["message"] and "Zůstalo 1 běhů spárovaných se závody." in job["message"]
    assert "Smazáno 2 ostatních běhů; ty se vrátí jen opětovným nahráním exportu." in job["message"]
    acts = con.execute("SELECT * FROM activities").fetchall()
    assert len(acts) == 1 and acts[0]["source"] == "garmin-export"
    conf = app.config["OB"]
    assert os.listdir(conf.path("incoming")) == []                       # the zip is gone
    kept = [f for _, _, fs in os.walk(conf.path("fit")) for f in fs]
    assert len(kept) == 1                                                # and so are the unpaired runs
    e = con.execute("SELECT e.* FROM entries e JOIN classes c ON c.id = e.class_id JOIN events ev ON ev.id = c.event_id"
                    " WHERE ev.oris_id = 8989").fetchone()
    assert e["activity_id"] == acts[0]["id"] and e["match_confidence"] == "high"
    # a single .fit uploaded by hand is never dropped, paired or not
    with open(inputs("azymut-e5")[2], "rb") as f:
        client.post("/upload", data=dict(csrf_token=csrf(client), files=(io.BytesIO(f.read()), "x.fit")),
                    content_type="multipart/form-data")
    work(app)
    assert con.execute("SELECT COUNT(*) FROM activities").fetchone()[0] == 2


def test_garmin_export_loads_the_races_first_and_keeps_unpaired_runs_at_a_race(app, client, user, monkeypatch):
    """Nothing is known of the runner's races when the export comes: they are loaded from ORIS before the runs
    are paired. Of two runs at the race one is the race; the other is not paired, but it is not dropped with
    the ordinary runs either."""
    import zipfile

    from oroute import garmin
    ev = FakeOris().event(8989)                                  # Pohora, 17 May 2025, start 13:18, 50:22
    day = dt.date.fromisoformat(ev["date"])
    utc = lambda d, h, m: dt.datetime(d.year, d.month, d.day, h, m, tzinfo=dt.timezone.utc)
    run = lambda start, timer, pos: dict(type="activity", start=start, sport="running", sub_sport="generic",
                                         timer=timer, elapsed=timer, dist=timer * 3.0, first_gps=pos)
    at_race = [ev["lat"] + 0.004, ev["lon"]]
    runs = {b"race": run(utc(day, 11, 18), 3030.0, at_race),              # 13:18 local: the race
            b"warm-up": run(utc(day, 10, 30), 900.0, at_race),            # the same day and place, no race of its own
            b"at home": run(utc(day - dt.timedelta(days=3), 16, 0), 2400.0, [49.68, 18.35])}
    monkeypatch.setattr(garmin, "scan_fit", lambda data: runs.get(data, dict(error="not a fit")))
    export = io.BytesIO()
    with zipfile.ZipFile(export, "w") as z:
        for data in runs:
            z.writestr(data.decode().replace(" ", "_") + ".fit", data)
    con = con_of(app)
    assert con.execute("SELECT COUNT(*) FROM entries").fetchone()[0] == 0
    client.post("/upload", data=dict(csrf_token=csrf(client), files=(io.BytesIO(export.getvalue()), "export.zip")),
                content_type="multipart/form-data")
    work(app)
    job = con.execute("SELECT * FROM jobs WHERE kind = 'import_upload'").fetchone()
    assert job["status"] == "done", job["error"]
    assert "Závody z ORIS načteny." in job["message"]
    assert "Zůstalo 2 běhů: 1 spárovaných se závody a 1 nespárovaných u závodu" in job["message"]
    assert "Smazáno 1 ostatních běhů; ty se vrátí jen opětovným nahráním exportu." in job["message"]
    acts = {a["original_name"]: a for a in con.execute("SELECT * FROM activities")}
    assert sorted(acts) == ["race.fit", "warm-up.fit"]
    kept = [f for _, _, fs in os.walk(app.config["OB"].path("fit")) for f in fs]
    assert len(kept) == 2
    e = con.execute("SELECT e.* FROM entries e JOIN classes c ON c.id = e.class_id JOIN events ev ON ev.id = c.event_id"
                    " WHERE ev.oris_id = 8989").fetchone()
    assert e["activity_id"] == acts["race.fit"]["id"] and e["match_confidence"] == "high"
    # the list of uploaded runs offers to pair the other one with the race or to delete it
    html = client.get("/upload").get_data(as_text=True)
    other = acts["warm-up.fit"]["id"]
    assert html.count("nespárované u závodu") == 1 and f"/activities/{other}/delete" in html
    assert "Přiřadit: Mistrovství oblasti na krátké trati" in html
    assert f"/activities/{acts['race.fit']['id']}/delete" not in html
    # the run of the race cannot be deleted from there, the other one can; somebody else's run cannot either
    post(client, f"/activities/{acts['race.fit']['id']}/delete")
    assert con.execute("SELECT COUNT(*) FROM activities").fetchone()[0] == 2
    assert post(client, f"/races/{e['id']}/activity", activity_id=other).status_code == 302       # pair it by hand
    assert con.execute("SELECT activity_id FROM entries WHERE id = ?", (e["id"],)).fetchone()[0] == other
    assert f"/activities/{acts['race.fit']['id']}/delete" in client.get("/upload").get_data(as_text=True)
    assert post(client, f"/activities/{acts['race.fit']['id']}/delete").status_code == 302
    assert [a["original_name"] for a in con.execute("SELECT * FROM activities")] == ["warm-up.fit"]
    assert len([f for _, _, fs in os.walk(app.config["OB"].path("fit")) for f in fs]) == 1
    post(client, "/logout")
    register(client, "BFM0001")
    assert post(client, f"/activities/{other}/delete").status_code == 404


def test_garmin_export_survives_oris_being_down(app, client, user):
    import zipfile

    from webapp import oris

    class Down(FakeOris):
        def user(self, regno):
            raise oris.OrisError("ORIS getUser: timed out")
    app.config["OB"].oris_client = Down()
    export = io.BytesIO()
    with zipfile.ZipFile(export, "w") as z:            # an account export (one run in it)
        with open(inputs("pohora")[2], "rb") as f:
            z.writestr("DI_CONNECT/DI-Connect-Uploaded-Files/pohora.fit", f.read())
    client.post("/upload", data=dict(csrf_token=csrf(client), files=(io.BytesIO(export.getvalue()), "export.zip")),
                content_type="multipart/form-data")
    work(app)
    job = con_of(app).execute("SELECT * FROM jobs WHERE kind = 'import_upload'").fetchone()
    assert job["status"] == "done", job["error"]
    assert "ORIS teď neodpovídá" in job["message"] and "Smazáno 1 ostatních běhů" in job["message"]


def test_picture_of_a_map_needs_the_track_and_official_times(app, client, user):
    con, _ = synced(app, client, user)
    mine = con.execute("SELECT e.id FROM entries e JOIN classes c ON c.id = e.class_id JOIN events ev"
                       " ON ev.id = c.event_id WHERE ev.oris_id = 8989").fetchone()["id"]
    page = f"/races/{mine}"

    def send(kind, name, data):
        return client.post(page + "/map", data=dict(csrf_token=csrf(client), kind=kind, kmz=(io.BytesIO(data), name)),
                           content_type="multipart/form-data", follow_redirects=True).get_data(as_text=True)
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (800, 600), (255, 255, 255)).save(buf, "PNG")
    assert "jen jako mapu s tratí" in send("maponly", "scan.png", buf.getvalue())
    assert "chybí běh z hodinek" in send("course", "scan.png", buf.getvalue())           # no activity yet
    with open(inputs("pohora")[2], "rb") as f:
        client.post("/upload", data=dict(csrf_token=csrf(client), files=(io.BytesIO(f.read()), "run.fit")),
                    content_type="multipart/form-data")
    work(app)
    assert con.execute("SELECT activity_id FROM entries WHERE id = ?", (mine,)).fetchone()[0]
    assert "není obrázek" in send("course", "scan.jpg", b"not a picture")
    small = io.BytesIO()
    Image.new("RGB", (200, 200)).save(small, "PNG")
    assert "příliš malý" in send("course", "scan.png", small.getvalue())
    # a blank picture is accepted, queued, and the worker says why it could not be placed
    con.execute("DELETE FROM jobs")
    con.commit()
    assert "Usazuje se na pozadí" in send("course", "scan.png", buf.getvalue())
    work(app)
    job = con.execute("SELECT * FROM jobs WHERE kind = 'georef_map'").fetchone()
    assert job["status"] == "failed" and "nejsou vidět fialová kolečka" in job["error"]
    assert not os.listdir(app.config["OB"].path("incoming"))          # the upload is gone either way


def test_queue_does_not_duplicate_waiting_jobs(app):
    con = con_of(app)
    con.execute("INSERT INTO users (username, password_hash) VALUES ('u', 'x')")
    a = jobs.enqueue(con, "refit_model", user_id=1)
    assert jobs.enqueue(con, "refit_model", user_id=1) == a
    assert jobs.claim(con)["id"] == a and jobs.claim(con) is None
    assert jobs.enqueue(con, "refit_model", user_id=1) != a  # the first one is already running


def test_quick_jobs_go_before_analyses(app):
    con = con_of(app)
    con.execute("INSERT INTO users (username, password_hash) VALUES ('u', 'x')")
    slow = jobs.enqueue(con, "analyse", user_id=1, payload=dict(refit=True))
    quick = jobs.enqueue(con, "sync_oris", user_id=1)
    assert [jobs.claim(con)["id"], jobs.claim(con)["id"]] == [quick, slow]


@pytest.mark.needs_data
def test_run_and_both_maps_in_one_form(app, client, user):
    """The form on the race page takes the run and both maps at once: the run is paired with that race by hand
    and the analysis is queued once, not once per file."""
    con, _ = synced(app, client, user)
    mine = con.execute("SELECT e.id FROM entries e JOIN classes c ON c.id = e.class_id JOIN events ev"
                       " ON ev.id = c.event_id WHERE ev.oris_id = 8989").fetchone()["id"]
    page = f"/races/{mine}"
    html = client.get(page).get_data(as_text=True)
    # nothing is there yet: the page opens on the tab where the files go and says what is missing
    assert 'data-vychozi="podklady"' in html and html.count('data-tab="podklady"') == 3
    course, maponly, fit = inputs("pohora")
    files = {name: (open(path, "rb"), os.path.basename(path)) for name, path in
             (("fit", fit), ("course", course), ("maponly", maponly))}
    r = client.post(page + "/files", data=dict(csrf_token=csrf(client), **files), content_type="multipart/form-data",
                    headers={"X-Requested-With": "XMLHttpRequest"})
    assert r.get_json() == dict(redirect=page)           # sent by script: the address to go to, no redirect
    e = con.execute("SELECT * FROM entries WHERE id = ?", (mine,)).fetchone()
    assert e["activity_id"] and e["match_confidence"] == "manual"
    queued = con.execute("SELECT kind, entry_id FROM jobs").fetchall()
    assert [tuple(j) for j in queued] == [("analyse", mine)]
    html = client.get(page).get_data(as_text=True)
    assert "spárovaný s tímhle závodem" in html and "uložená pro kategorii" in html and "uložená pro všechny" in html
    assert 'class="ob-kroky"' not in html                # nothing is missing any more
    # a file that is not a run is refused, and nothing chosen is said so
    r = client.post(page + "/files", data=dict(csrf_token=csrf(client), fit=(io.BytesIO(b"x"), "photo.fit")),
                    content_type="multipart/form-data", follow_redirects=True)
    assert "není aktivita Garmin" in r.get_data(as_text=True)
    r = client.post(page + "/files", data=dict(csrf_token=csrf(client)), follow_redirects=True)
    assert "Vyber aspoň jeden soubor" in r.get_data(as_text=True)
    # the two switches of the race are one form: saved together, routes recalculated once. They are the
    # runner's own; the race keeps its values for everybody else
    assert post(client, page + "/settings", osm_mode="off", hatch_mode="off").status_code == 302
    assert tuple(con.execute("SELECT own_osm_mode, own_hatch_mode FROM entries WHERE id = ?", (mine,)).fetchone()) \
        == ("off", "off")
    ev = con.execute("SELECT osm_mode, hatch_mode FROM events WHERE oris_id = 8989").fetchone()
    assert tuple(ev) == ("forbid", "forbid")


def test_race_list_shows_races_with_a_run_and_keeps_the_season(app, client, user):
    con, _ = synced(app, client, user)
    assert "Tomuhle filtru žádný závod neodpovídá" in client.get("/?jen=beh").get_data(as_text=True)
    mine = con.execute("SELECT e.id FROM entries e JOIN classes c ON c.id = e.class_id JOIN events ev"
                       " ON ev.id = c.event_id WHERE ev.oris_id = 8989").fetchone()["id"]
    with open(inputs("pohora")[2], "rb") as f:
        client.post(f"/races/{mine}/files", data=dict(csrf_token=csrf(client), fit=(f, "run.fit")),
                    content_type="multipart/form-data")
    html = client.get("/?jen=beh").get_data(as_text=True)
    assert "na krátké trati" in html and "na dlouhé trati" not in html
    assert f'href="/races/{mine}#podklady"' in html      # the state "map missing" leads to where it is added
    # the season chosen once is still chosen on the next visit, until another one is picked
    client.get("/?sezona=2026")
    assert "na krátké trati" not in client.get("/").get_data(as_text=True)
    assert "na krátké trati" in client.get("/?sezona=").get_data(as_text=True)


def test_failed_job_can_be_queued_again(app, client, user):
    con = con_of(app)
    jid = jobs.enqueue(con, "sync_oris", user_id=user)
    con.execute("UPDATE jobs SET status = 'failed', error = 'ORIS getUser: timed out' WHERE id = ?", (jid,))
    con.commit()
    assert f"/jobs/{jid}/retry" in client.get("/jobs").get_data(as_text=True)
    assert post(client, f"/jobs/{jid}/retry").status_code == 302
    rows = [tuple(j) for j in con.execute("SELECT kind, status FROM jobs ORDER BY id")]
    assert rows == [("sync_oris", "failed"), ("sync_oris", "queued")]
    # the old failure is no longer the last word: no button next to it, and somebody else cannot use it
    assert f"/jobs/{jid}/retry" not in client.get("/jobs").get_data(as_text=True)
    post(client, "/logout")
    register(client, "BFM0001")
    assert post(client, f"/jobs/{jid}/retry").status_code == 404


def test_single_fit_from_a_race_not_loaded_yet_loads_the_races_from_oris(app, client, user):
    """A .fit from last weekend's race, uploaded before the race list was refreshed: the race is loaded from
    ORIS (as with a Garmin export) and the run is paired with it, so the race shows up to add a map to."""
    con = con_of(app)
    assert con.execute("SELECT COUNT(*) FROM entries").fetchone()[0] == 0
    with open(inputs("pohora")[2], "rb") as f:
        client.post("/upload", data=dict(csrf_token=csrf(client), files=(io.BytesIO(f.read()), "pohora.fit")),
                    content_type="multipart/form-data")
    work(app)
    job = con.execute("SELECT * FROM jobs WHERE kind = 'import_upload'").fetchone()
    assert job["status"] == "done", job["error"]
    assert "Závody z ORIS načteny. Spárováno se závodem." in job["message"]
    e = con.execute("SELECT e.* FROM entries e JOIN classes c ON c.id = e.class_id JOIN events ev ON ev.id = c.event_id"
                    " WHERE ev.oris_id = 8989").fetchone()
    assert e["activity_id"] is not None


def test_single_fit_on_a_known_race_day_does_not_ask_oris(app, client, user):
    con, _ = synced(app, client, user)
    with open(inputs("pohora")[2], "rb") as f:
        client.post("/upload", data=dict(csrf_token=csrf(client), files=(io.BytesIO(f.read()), "pohora.fit")),
                    content_type="multipart/form-data")
    work(app)
    msg = con.execute("SELECT message FROM jobs WHERE kind = 'import_upload'").fetchone()["message"]
    assert "ORIS" not in msg and "Spárováno se závody: 1." in msg
