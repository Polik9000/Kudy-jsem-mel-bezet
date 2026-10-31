"""The four races through the web app: upload -> queue -> worker -> SQLite -> pages (about 8 minutes)."""
import datetime as dt
import json
import os
import shutil

import numpy as np
import pytest
from conftest import FakeOris, clear_jobs, post, register
from races import GOLDEN, ROOT

from oroute import osm
from oroute import personal as fitter
from webapp import create_app
from webapp import db as dbm
from webapp.seed import seed_demo
from webapp.services import jobs, personal
from webapp.worker import load_handlers, run_once

pytestmark = pytest.mark.slow

# start-to-finish times: Azymut from GPS (not in ORIS), Pohora and Petřvald from the official ORIS times
TOTALS = {"azymut-e5": 77 * 60 + 2, "azymut-e4": 55 * 60 + 7, "pohora": 50 * 60 + 22, "petrvald": 80 * 60 + 18}


def fake_osm(south, west, north, east):
    if south < 49.83 < north and west < 18.37 < east:
        with open(os.path.join(ROOT, "tests", "fixtures", "osm", "petrvald_overpass.json"), encoding="utf-8") as f:
            return dict(osm.parse(json.load(f)), fetched="2026-10-06")
    return dict(lines=[], crossings=[], fetched="2026-10-06")


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    app = create_app(str(tmp_path_factory.mktemp("site") / "instance"))
    app.config["TESTING"] = True
    client = app.test_client()
    app.config["OB"].oris_client = FakeOris()
    # no network: elevation from tests/golden, OpenStreetMap from the saved Overpass answer (Petřvald) or nothing
    app.config["OB"].dem = "aws"
    app.config["OB"].osm_fetch = fake_osm
    assert register(client).status_code == 302
    clear_jobs(app)
    conf = app.config["OB"]
    con = dbm.connect(conf.db_path)
    uid = con.execute("SELECT id FROM users").fetchone()["id"]
    entries = seed_demo(con, conf, uid, refit=False)
    # elevation tiles from tests/golden, so no network is needed
    os.makedirs(conf.path("dem"))
    for folder, entry_id in entries.items():
        event = con.execute("SELECT c.event_id FROM entries e JOIN classes c ON c.id = e.class_id WHERE e.id = ?",
                            (entry_id,)).fetchone()[0]
        shutil.copyfile(os.path.join(GOLDEN, folder, "dem_cache.npz"), conf.path("dem", f"event_{event}.npz"))
    load_handlers()
    run_once(conf)
    jobs.enqueue(con, "refit_model", user_id=uid)
    run_once(conf)
    failed = [dict(j) for j in con.execute("SELECT kind, entry_id, error FROM jobs WHERE status != 'done'")]
    assert not failed, failed
    return dict(app=app, client=client, con=con, conf=conf, uid=uid, entries=entries)


def analysis(site, folder):
    return site["con"].execute("SELECT * FROM analyses WHERE entry_id = ?", (site["entries"][folder],)).fetchone()


@pytest.mark.parametrize("folder", list(TOTALS))
def test_total_times(site, folder):
    a = analysis(site, folder)
    assert a["has_routes"] == 1 and round(a["total_time_s"]) == TOTALS[folder]
    official = dbm.loads(a["summary"])["official"]
    if folder.startswith("azymut"):
        assert official is None            # not in ORIS: punches from GPS
    else:
        assert official["used"]            # ORIS first


def test_race_page_and_data(site):
    eid = site["entries"]["pohora"]
    html = site["client"].get(f"/races/{eid}").get_data(as_text=True)
    assert "50:22" in html and "oficiální mezičasy z ORIS" in html and 'id="map"' in html
    d = site["client"].get(f"/races/{eid}/data.json").get_json()
    assert set(d["maps"]) == {"maponly", "course"} and len(d["maps"]["maponly"]["corners"]) == 3
    assert len(d["legs"]) == 17 and len(d["course"]) == 18
    assert all(l["best_route"] and l["explain"] for l in d["legs"])
    # leg times are the official splits (S-1 1:24, finish leg 0:10)
    assert round(d["legs"][0]["time"]) == 84 and d["legs"][0]["official"] == 84 and round(d["legs"][-1]["time"]) == 10
    assert abs(sum(l["time"] for l in d["legs"]) - 3022) < 0.5


def test_model_is_the_plain_fit_when_there_are_no_notes(site):
    con, conf = site["con"], site["conf"]
    row = con.execute("SELECT * FROM speed_models WHERE user_id = ? ORDER BY id DESC", (site["uid"],)).fetchone()
    stored = dbm.loads(row["model"])
    paths = [conf.path(analysis(site, f)["out_dir"], "best", "fit_samples.npz") for f in TOTALS]
    want = fitter.fit(fitter.load(sorted(paths)), today=dt.date.today()).to_dict()
    assert abs(stored["v_flat"] - want["v_flat"]) < 1e-9
    assert all(abs(stored["factors"][k] - v) < 1e-9 for k, v in want["factors"].items())
    assert len(stored["notes"]["personal"]["races"]) == 4
    html = site["client"].get("/model").get_data(as_text=True)
    assert "Terény" in html and "Kopce" in html and "les (dobře průběžný)" in html


def test_notes_change_the_loss_and_the_model(site):
    con, client = site["con"], site["client"]
    eid = site["entries"]["azymut-e5"]
    url = f"/races/{eid}/legs/8/note"       # leg 7-8: 49 s standing still
    token = client.get("/profile").get_data(as_text=True).split('name="csrf_token" value="')[1].split('"')[0]
    send = lambda body: client.post(url, json=body, headers={"X-CSRF-Token": token})
    before = client.get(f"/races/{eid}/data.json").get_json()["legs"][7]
    stop = before["stop_time"]
    assert round(stop) == 49 and before["deliberate_s"] == 0 and "stání 49 s" in before["flags"]
    r = send(dict(deliberate_stop=True, text="tkanička", fatigue=2, green="through",
                  planned=[[49.96, 21.85], [49.961, 21.851]]))
    after = r.get_json()["legs"][7]
    assert "best_route" not in after and "alts" not in after   # numbers only: the page keeps the routes it has
    assert after["deliberate_s"] == stop and abs(before["loss_exec"] - after["loss_exec"] - stop) < 1e-6
    assert after["loss_route"] == before["loss_route"] and not any("stání" in f for f in after["flags"])
    assert after["note"]["text"] == "tkanička" and after["note"]["planned"] == [[49.96, 21.85], [49.961, 21.851]]
    assert r.get_json()["totals"]["deliberate"] == stop
    # the change queued a refit of the personal model
    assert con.execute("SELECT COUNT(*) FROM jobs WHERE kind = 'refit_model' AND status = 'queued'").fetchone()[0] == 1
    # lost contact with the map takes a clean leg out of the model
    reads, _ = personal.leg_reads(con, eid, analysis(site, "azymut-e5")["id"], 1)
    clean = next(n for n, rd in reads.items() if rd["in_model"])
    n_before = len(np.concatenate([r["leg_ids"] for r in personal.user_races(con, site["conf"], site["uid"])]))
    client.post(f"/races/{eid}/legs/{clean}/note", json=dict(lost_contact=True), headers={"X-CSRF-Token": token})
    n_after = len(np.concatenate([r["leg_ids"] for r in personal.user_races(con, site["conf"], site["uid"])]))
    assert n_after == n_before - 1
    run_once(site["conf"])
    last = con.execute("SELECT * FROM jobs WHERE kind = 'refit_model' ORDER BY id DESC LIMIT 1").fetchone()
    assert last["status"] == "done" and "přepočítán" in last["message"]
    # the line drawn as the planned route of leg 7-8 was priced in the same run of the worker, with the terrain,
    # the elevation and the model of the analysis
    job = con.execute("SELECT * FROM jobs WHERE kind = 'price_plans' ORDER BY id DESC LIMIT 1").fetchone()
    assert job["status"] == "done" and job["message"] == "Plánované postupy oceněny modelem: 1."
    plan = client.get(f"/races/{eid}/data.json").get_json()["legs"][7]["note"]["plan"]
    assert plan["time"] > 20 and 100 < plan["dist"] < 170 and plan["text"].startswith("Plán")
    assert send(dict(fatigue=7)).status_code == 400 and send(dict(green="x")).status_code == 400


def test_petrvald_road_is_not_a_building(site):
    """Leg 2-3 of Petřvald crosses a road drawn 9 pixels wide (0.59 m per pixel). Read as a building it sent
    the best route 500 m round its end; the runner ran 365 m and the class needs 2:21."""
    leg = next(l for l in _data(site, "petrvald")["legs"] if l["name"] == "2-3")
    assert leg["best"]["dist"] < 400 and leg["best"]["time"] < 170, leg["best"]
    # the terrain was read once for the event and kept for the next analysis
    event = site["con"].execute("SELECT c.event_id FROM entries e JOIN classes c ON c.id = e.class_id WHERE e.id = ?",
                                (site["entries"]["petrvald"],)).fetchone()[0]
    assert os.path.exists(site["conf"].path("terrain", f"event_{event}.npz"))


def test_rerun_draws_the_race_with_the_current_model(site):
    con, client = site["con"], site["client"]
    eid = site["entries"]["azymut-e5"]
    latest = con.execute("SELECT id FROM speed_models ORDER BY id DESC").fetchone()["id"]
    assert analysis(site, "azymut-e5")["model_id"] != latest
    assert "Postupy jsou spočítané se starším modelem rychlosti." in client.get(f"/races/{eid}").get_data(as_text=True)
    n_jobs = con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    post(client, f"/races/{eid}/reanalyse")
    run_once(site["conf"])
    # one job did it all: the race joined the model first, then its routes were found once
    done = con.execute("SELECT * FROM jobs WHERE id > ? ORDER BY id", (n_jobs,)).fetchall()
    assert [(j["kind"], j["status"]) for j in done] == [("analyse", "done")], [dict(j) for j in done]
    a = analysis(site, "azymut-e5")
    assert a["model_id"] == con.execute("SELECT id FROM speed_models ORDER BY id DESC").fetchone()["id"]
    assert round(a["total_time_s"]) == TOTALS["azymut-e5"]
    # the web does not keep the pictures the scripts draw for their reports
    out = site["conf"].path(a["out_dir"])
    assert os.path.exists(os.path.join(out, "best", "best.json"))
    assert not [f for d in (out, os.path.join(out, "best")) for f in os.listdir(d) if f.endswith((".jpg", ".png"))]
    # the notes survived the re-analysis
    assert client.get(f"/races/{eid}/data.json").get_json()["legs"][7]["note"]["text"] == "tkanička"


# --- checks of the best routes on the real races (docs/pruzkum.md part 6) --------------------------------

def _data(site, folder):
    return site["client"].get(f"/races/{site['entries'][folder]}/data.json").get_json()


# Legs where the check below is known to fail, with the reason. Empty since 7 Oct 2026: the one leg it found
# (Petřvald 2-3: on a map with 0.59 m per pixel a road 9 pixels wide was read as a building and the route went
# round its end) is fixed, oroute/terrain.py scales its sizes in pixels with the resolution of the map.
KNOWN_DETOURS = set()


@pytest.mark.parametrize("folder", list(TOTALS))
def test_best_routes_are_consistent(site, folder):
    d = _data(site, folder)
    with_alts = 0
    for l in d["legs"]:
        best, line = l["best"]["time"], l["line"]["time"]
        if (folder, l["name"]) in KNOWN_DETOURS:
            continue
        # the best route is not slower than the line that was run, priced by the same model. Allowance: the
        # route is found on 2-pixel cells and priced on the full map, and the line that was run starts and
        # ends where the GPS was at the punch, up to 10-20 m from the control (short legs: Pohora 15-16)
        assert best <= line * 1.05 + 15, (folder, l["name"], best, line)
        # loss by route choice + loss by execution = total loss of the leg
        assert abs(l["loss_route"] + l["loss_exec"] - l["loss_total"]) < 1e-6
        # alternatives: other routes, never clearly faster than the best one, with a real line to draw
        for a in l["alts"]:
            assert a["delta"] >= -(0.03 * best + 3) and len(a["route"]) >= 2 and a["dist"] > 0
        assert len(l["alts"]) <= 2 and isinstance(l["balanced"], bool)
        with_alts += bool(l["alts"])
    assert with_alts >= 3, folder


def _segments_cross(p1, p2, p3, p4):
    return osm._cross(p1, p2, p3, p4)


def test_petrvald_route_14_15_respects_the_railway(site):
    """The known wrong route: leg 14-15 used to go straight across the railway. With the railway from
    OpenStreetMap it may only cross at a level crossing, bridge or underpass."""
    d = _data(site, "petrvald")
    rails = [l["line"] for l in d["osm"]["lines"] if l["kind"] == "forbidden"]
    assert len(rails) == 2 and len(d["osm"]["crossings"]) == 3
    k = 111195.0
    far = []
    for leg in d["legs"]:
        for route in [leg["best_route"]] + [a["route"] for a in leg["alts"]]:
            for p1, p2 in zip(route, route[1:]):
                for rail in rails:
                    for p3, p4 in zip(rail, rail[1:]):
                        x = _segments_cross(p1, p2, p3, p4)
                        if x:
                            m = min(((x[0] - c[0]) * k) ** 2 + ((x[1] - c[1]) * k * 0.645) ** 2
                                    for c in d["osm"]["crossings"]) ** 0.5
                            far.append((leg["name"], round(m)))
    assert far and all(m <= 25 for _, m in far), far          # some legs do cross, all of them at a crossing
    assert "14-15" in {name for name, _ in far}
    # the leg is longer than the straight run across the rails the model used to suggest (8:45)
    leg = next(l for l in d["legs"] if l["name"] == "14-15")
    assert leg["best"]["time"] > 9.5 * 60
    # fences from OpenStreetMap are not used unless switched on
    b = analysis_summary(site, "petrvald")["barriers"]
    assert (b["forbidden"], b["hard"], b["crossings"]) == (2, 0, 3)
    assert all(l["what"] == "railway" for l in d["osm"]["lines"])


def _inside(p, ring):
    """Point in polygon (ray casting), both as [lat, lon]."""
    n = False
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if (a[0] > p[0]) != (b[0] > p[0]) and p[1] < a[1] + (p[0] - a[0]) * (b[1] - a[1]) / (b[0] - a[0]):
            n = not n
    return n


def test_petrvald_routes_keep_out_of_the_hatched_fields(site):
    """The map with the course of Petřvald H18 has fields and a road hatched as out of bounds (oroute/hatch.py):
    the page draws them and no best route or alternative leads through them."""
    d = _data(site, "petrvald")
    assert 5 <= len(d["areas"]) <= 12
    assert analysis_summary(site, "petrvald")["barriers"]["areas"] == len(d["areas"])
    through = [(leg["name"], p) for leg in d["legs"] for route in [leg["best_route"]] + [a["route"] for a in leg["alts"]]
               for p in route[1:-1] if any(_inside(p, ring) for ring in d["areas"])]
    assert not through, through[:5]
    for folder in ("azymut-e5", "azymut-e4", "pohora"):
        assert _data(site, folder)["areas"] == []


def analysis_summary(site, folder):
    return dbm.loads(analysis(site, folder)["summary"])


def test_split_times_of_the_class_join_the_gps_analysis(site):
    d = _data(site, "pohora")
    assert all(l["ws"] is not None for l in d["legs"])                    # every leg has a loss by split times
    assert any(l["mistake"] for l in d["legs"])                          # and some a kind of mistake from the track
    assert all(l["mistake"]["label"] and l["mistake"]["text"] for l in d["legs"] if l["mistake"])
    html = site["client"].get(f"/races/{site['entries']['pohora']}").get_data(as_text=True)
    # the check of the model against the class is on the model page, the tab only points there
    assert "Graf mezičasů" in html and "Pořadová korelace" not in html and "#jak-sedi" in html
    model = site["client"].get("/model").get_data(as_text=True)
    assert "Jak dobře model sedí" in model and "Pořadová korelace" in model
    # Azymut is not in ORIS: no split times, the page still works
    d = _data(site, "azymut-e4")
    assert all(l["ws"] is None for l in d["legs"])
    assert 'id="mezicasy"' not in site["client"].get(f"/races/{site['entries']['azymut-e4']}").get_data(as_text=True)


def test_model_page_shows_uncertainty_and_the_leave_one_out_check(site):
    html = site["client"].get("/model").get_data(as_text=True)
    assert "nejistota" in html and "±" in html and 'class="ob-graf"' in html
    assert "předpověď z ostatních závodů" in html
    stored = dbm.loads(site["con"].execute("SELECT model FROM speed_models ORDER BY id DESC").fetchone()["model"])
    assert len(stored["notes"]["check"]) == 4
    assert all(0 < o["rel_se"] < 0.3 for o in stored["notes"]["terrain"].values())
