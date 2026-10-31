"""The planned route of a leg in the web app: drawn on the map, priced by the worker with the real script
(oroute/planned.py) on a small made-up map, shown next to the best route and the one that was run.
The same map has two paths that cross, for the catching features around a control (oroute/relocate.py)."""
import io
import json
import os
import zipfile

import numpy as np
import pytest
from conftest import clear_jobs, csrf, post, register
from PIL import Image
from races import inputs

import bestroute
from oroute import dem, relocate
from oroute import terrain as T
from oroute.kmzmap import GeoMap
from oroute.speedmodel import SpeedModel
from webapp import db as dbm
from webapp.services import personal, results, runner
from webapp.worker import load_handlers, run_once

SIDE, MPP = 600, 1.33
EDGE = 380                                   # open land west of this column of the map, green to walk through east of it
# start, 1, 2, finish in map pixels (well inside: the terrain reader takes the rim of a picture for its margin)
CONTROLS = [(140, 300), (300, 300), (460, 300), (460, 400)]


def made_up_map():
    """(KMZ bytes, GeoMap) of a map without course: yellow open land and a block of green, no header bar."""
    rgb = np.empty((SIDE, SIDE, 3), np.uint8)
    rgb[:, :EDGE] = (253, 190, 79)
    rgb[:, EDGE:] = (137, 202, 139)
    rgb[249:252, 100:500] = rgb[100:500, 249:252] = (35, 31, 32)      # two paths, a junction north-west of control 1
    image = Image.fromarray(rgb)
    lat, lon, half = 49.6, 18.3, SIDE * MPP / 2
    dlat, dlon = half / 111195.0, half / (111195.0 * np.cos(np.radians(lat)))
    gm = GeoMap(image, lat + dlat, lat - dlat, lon + dlon, lon - dlon)
    png, kmz = io.BytesIO(), io.BytesIO()
    image.save(png, "PNG")
    with zipfile.ZipFile(kmz, "w") as z:
        z.writestr("doc.kml", "<kml><!-- ob-header-px: 0 --><GroundOverlay><Icon><href>map.png</href></Icon><LatLonBox>"
                   f"<north>{gm.n:.9f}</north><south>{gm.s:.9f}</south><east>{gm.e:.9f}</east><west>{gm.w:.9f}</west>"
                   "</LatLonBox></GroundOverlay></kml>")
        z.writestr("map.png", png.getvalue())
    return kmz.getvalue(), gm


def flat_elevation(path, gm):
    """An elevation file as oroute/dem.py keeps it for the map: every tile at 300 m (no network in tests)."""
    x0, y0 = dem._tile_xy(gm.n, gm.w, 15)
    x1, y1 = dem._tile_xy(gm.s, gm.e, 15)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    np.savez_compressed(path, h=np.full((256 * (int(y1) - int(y0) + 1), 256 * (int(x1) - int(x0) + 1)), 300.0),
                        tx0=int(x0), ty0=int(y0), z=15)


def straight(gm, a, b, model):
    """Model time of the straight line between two points of the made-up map (flat)."""
    (u0, _), (u1, _) = a, b
    green = max(0, max(u0, u1) - max(EDGE, min(u0, u1))) * gm.m_per_px_x
    length = float(np.hypot(b[0] - a[0], b[1] - a[1])) * gm.m_per_px_x
    return (length - green) / (model.v_flat * model.factors[T.OPEN]) + green / (model.v_flat * model.factors[T.WALK])


def scripts(gm, times):
    """Stand-in for analyze.py and bestroute.py on the made-up map (three legs, the track runs straight from
    control to control in `times` seconds); oroute/planned.py and oroute/relocate.py are run for real."""
    real, model = runner._run, SpeedModel()
    ll = lambda p: [round(float(x), 6) for x in gm.px_to_latlon(*p)]
    pts = [ll(p) for p in CONTROLS]
    names = ("S-1", "1-2", "2-F")

    def run(*cmd, on_line=None):
        if cmd[:2] in (("-m", "oroute.planned"), ("-m", "oroute.relocate")):
            return real(*cmd, on_line=on_line)
        if cmd[:2] == ("-m", "oroute.hatch"):
            with open(cmd[3], "w") as f:
                json.dump(dict(areas=[]), f)
        elif cmd[0] == "analyze.py":
            course = [dict(lat=la, lon=lo) for la, lo in pts]
            with open(os.path.join(cmd[3], "course.json"), "w") as f:
                json.dump(dict(start=course[0], controls=course[1:-1], finish=course[-1]), f)
            legs = [dict(leg=k, name=n, time=times[k - 1], est_loss=5.0, stops=[], a=k - 1, b=k, straight=200.0,
                         run=200.0, climb=0.0, stop_time=0.0, flags=[]) for k, n in enumerate(names, 1)]
            cum = [0.0] + [float(t) for t in np.cumsum(times)]
            with open(os.path.join(cmd[3], "analysis.json"), "w") as f:
                json.dump(dict(start="2026-03-28T09:00:00+00:00", total_time=cum[-1], est_loss=15.0, vref=3.0, rref=1.0,
                               offset_m=[0, 0], weak_order=[], official=None, course=course, punch=[0, 1, 2, 3],
                               track=dict(t=cum, lat=[p[0] for p in pts], lon=[p[1] for p in pts], speed=[3.0] * 4),
                               legs=legs), f)
        elif "--samples-only" in cmd:
            open(os.path.join(cmd[4], "leg_samples.npz"), "wb").close()
        else:
            legs = []
            for k, n in enumerate(names, 1):
                t = straight(gm, CONTROLS[k - 1], CONTROLS[k], model)
                dist = float(np.hypot(*np.subtract(CONTROLS[k], CONTROLS[k - 1]))) * gm.m_per_px_x
                m = dict(time=t, dist=dist, climb=0.0, mix={"open land": dist})
                legs.append(dict(leg=k, name=n, actual=times[k - 1], best=m, yours=m, straight=m,
                                 route=[pts[k - 1], pts[k]], text_cs="rovně", text_en="straight",
                                 # on the first leg the track cut a railway away from a crossing
                                 crossed=[dict(kind="line", what="railway", at=pts[0])] if k == 1 else []))
            with open(os.path.join(cmd[4], "best.json"), "w") as f:
                json.dump(dict(version=bestroute.VERSION, dem="aws", barriers=None, legs=legs), f)
            model.save(os.path.join(cmd[4], "speed_model.json"))
    return run


def work(app):
    load_handlers()
    return run_once(app.config["OB"])


@pytest.mark.needs_data
def test_planned_route_is_priced_by_the_model(app, client, user, monkeypatch):
    con, conf = dbm.connect(app.config["OB"].db_path), app.config["OB"]
    page = post(client, "/races/new", name="Trénink na louce", date="2026-03-28", class_name="T").headers["Location"]
    entry = int(page.rsplit("/", 1)[1])
    kmz, gm = made_up_map()
    model = SpeedModel()
    best = [straight(gm, a, b, model) for a, b in zip(CONTROLS, CONTROLS[1:])]
    times = [best[0] + 4, best[1] + 63, best[2] + 2]      # leg 1-2 lost a minute while it was run
    with open(inputs("pohora")[2], "rb") as fit:
        r = client.post(page + "/files", content_type="multipart/form-data", data=dict(
            csrf_token=csrf(client), fit=(fit, "run.fit"), course=(io.BytesIO(kmz), "course.kmz"),
            maponly=(io.BytesIO(kmz), "maponly.kmz")))
    assert r.status_code == 302
    event = con.execute("SELECT c.event_id FROM entries e JOIN classes c ON c.id = e.class_id").fetchone()[0]
    flat_elevation(conf.path("dem", f"event_{event}.npz"), gm)
    monkeypatch.setattr(runner, "_run", scripts(gm, times))
    monkeypatch.setattr(personal, "refit", lambda con, conf, uid, fresh=None: (None, False))
    work(app)
    assert [tuple(j) for j in con.execute("SELECT kind, status, error FROM jobs")] == [("analyse", "done", None)]
    html = client.get(page).get_data(as_text=True)
    assert f"{page}/legs.json" in html and 'id="p-plan"' in html

    # the same analysis looked round every control: the junction of the two paths, 94 m north-west of control 1,
    # is something to catch there and, lying on the way in from the start, the point to attack the control from
    assert 'id="p-ztrata"' in html and 'id="c-zachyt"' in html
    seen = client.get(page + "/data.json").get_json()["legs"]
    first = seen[0]["relocate"]
    assert first["lost"] is None and first["features"][0]["label"] == "křížení cest" and first["features"][0]["point"]
    assert first["features"][0]["where"] in ("křížení cest 94 m od kontroly na azimut 315°",
                                             "křížení cest 93 m od kontroly na azimut 315°")
    assert first["features"][0]["back"].endswith("m na azimut 135°, po rovině")
    assert "cesta, nejblíž" in " ".join(f["where"] for f in first["features"])
    assert seen[0]["attack"]["label"].startswith("křížení cest 9") and seen[2]["relocate"] is None  # the finish
    # a path through the meadow is not the edge of the meadow: that is where the green begins, east of the control
    assert [f["where"][-4:] for f in first["features"] if f["label"] == "okraj otevřené plochy"] == [" 90°"]
    # the leg runs on east from control 1: the edge of the green stops whoever ran past it; the path that
    # stops north of control 2 is an end, not a junction
    stop = seen[0]["beyond"]
    assert ", rovně okraj otevřené plochy 10" in stop["label"] and stop["label"].startswith("vlevo cesta ")
    assert stop["text"].endswith(" m. Kdo tam doběhne, kontrolu přeběhl a vrací se na azimut 270°")
    ahead = stop["parts"][1]
    assert ahead["label"].startswith("rovně okraj otevřené plochy 10") and len(ahead["line"]) == 5
    assert abs(ahead["lon"] - gm.px_to_latlon(380, 300)[1]) < 1e-4 and seen[2]["beyond"] is None
    # what the track went through that the routes must not is said with the leg, and where
    assert seen[0]["crossed"]["text"].startswith("Tvoje stopa kříží železnici mimo přechod.")
    assert len(seen[0]["crossed"]["at"]) == 1 and seen[1]["crossed"] is None
    assert client.get(page + "/legs.json").get_json()["legs"][0]["crossed"] == seen[0]["crossed"]
    assert [f["label"] for f in seen[1]["relocate"]["features"]][0] == "konec cesty"

    # An analysis from before the catching features (it kept the nearest junction as the attack point, whatever
    # side of the control it lay on) says so, shows no attack point and offers a short job that finds them
    # without finding the routes again.
    assert results.RELOCATE == relocate.VERSION and "Přepočítat záchytné body" not in html
    for row in con.execute("SELECT id, data FROM legs").fetchall():
        old = dict(json.loads(row["data"]), attack=dict(kind="junction", lat=49.6, lon=18.3, dist=68.0))
        old.pop("relocate", None), old.pop("beyond", None)
        con.execute("UPDATE legs SET data = ? WHERE id = ?", (json.dumps(old), row["id"]))
    con.execute("UPDATE analyses SET summary = json_remove(summary, '$.relocate')")
    con.commit()
    html = client.get(page).get_data(as_text=True)
    assert "Přepočítat záchytné body" in html and "tenhle rozbor ještě nemá" in html
    assert all(l["attack"] is None and l["relocate"] is None and l["beyond"] is None
               for l in client.get(page + "/data.json").get_json()["legs"])
    assert post(client, page + "/relocate").status_code == 302
    assert "Záchytné body u kontrol: čeká ve frontě." in client.get(page).get_data(as_text=True)
    work(app)
    assert [tuple(j) for j in con.execute("SELECT kind, status FROM jobs")] == [("analyse", "done"), ("relocate", "done")]
    again = client.get(page + "/data.json").get_json()["legs"][0]
    assert again["relocate"] == first and again["beyond"] == stop and again["attack"] == seen[0]["attack"]
    assert "Přepočítat záchytné body" not in client.get(page).get_data(as_text=True)
    con.execute("UPDATE analyses SET summary = json_set(summary, '$.relocate', 1)")       # an older version of the rules
    con.commit()
    assert "jsou ze starší verze výpočtu" in client.get(page).get_data(as_text=True)
    con.execute("UPDATE analyses SET summary = json_set(summary, '$.relocate', ?)", (results.RELOCATE,))
    con.commit()
    # Routes of an older bestroute.py (they could run through a pond or fenced ground) are offered to be found
    # again; that finds the catching features too, so one offer is enough.
    assert results.ROUTES == bestroute.VERSION
    assert "Nejlepší postupy jsou ze starší verze výpočtu" not in client.get(page).get_data(as_text=True)
    con.execute("UPDATE analyses SET summary = json_set(json_set(summary, '$.routes', 1), '$.relocate', 1)")
    con.commit()
    html = client.get(page).get_data(as_text=True)
    assert "Nejlepší postupy jsou ze starší verze výpočtu" in html and "Přepočítat záchytné body" not in html
    con.execute("UPDATE analyses SET summary = json_set(json_set(summary, '$.routes', ?), '$.relocate', ?)",
                (results.ROUTES, results.RELOCATE))
    con.commit()

    token = csrf(client)
    ll = lambda *p: [float(x) for x in gm.px_to_latlon(*p)]
    save = lambda n, **body: client.post(f"{page}/legs/{n}/note", json=body, headers={"X-CSRF-Token": token})
    legs = lambda: client.get(page + "/legs.json").get_json()
    kinds = lambda: [tuple(j) for j in con.execute("SELECT kind, status FROM jobs WHERE kind = 'price_plans' ORDER BY id")]

    # a plan drawn round the north on leg S-1: saved at once, priced by the worker a moment later
    detour = [ll(*CONTROLS[0]), ll(220, 180), ll(*CONTROLS[1])]
    d = save(1, planned=detour).get_json()
    assert d["legs"][0]["note"]["planned"] and d["legs"][0]["note"]["plan"] is None and d["plans_pending"]
    assert kinds() == [("price_plans", "queued")]
    assert "Ocenění plánovaného postupu: čeká ve frontě." in client.get(page).get_data(as_text=True)
    work(app)
    d = legs()
    plan = d["legs"][0]["note"]["plan"]
    assert not d["plans_pending"] and kinds() == [("price_plans", "done")]
    length = 2 * np.hypot(80, 120) * gm.m_per_px_x
    want = length / (model.v_flat * model.factors[T.OPEN])
    assert abs(plan["time"] - want) / want < 0.02 and abs(plan["dist"] - length) < 1 and plan["climb"] < 0.01
    assert abs(plan["delta"] - (want - best[0])) < 2
    assert plan["text"].startswith("Plán byl o 0:5") and "hlavně proto, že je o 17" in plan["text"]
    # the page draws from data.json: the plan stands next to the best route and the line that was run
    leg = client.get(page + "/data.json").get_json()["legs"][0]
    assert leg["note"]["plan"] == plan and leg["best"]["time"] == leg["line"]["time"] == best[0]

    # a note typed on the leg does not touch the numbers of its plan; nothing is priced again
    d = save(1, planned=d["legs"][0]["note"]["planned"], text="oběhl jsem to po louce").get_json()
    assert d["legs"][0]["note"]["plan"] == plan and not d["plans_pending"]
    # a straight plan on leg 1-2, over the open land and then through the green: fast then slow
    d = save(2, planned=[ll(*CONTROLS[1]), ll(*CONTROLS[2])]).get_json()
    assert d["legs"][1]["note"]["plan"] is None and d["legs"][0]["note"]["plan"] == plan
    work(app)
    two = legs()["legs"][1]["note"]["plan"]
    assert abs(two["time"] - best[1]) / best[1] < 0.03 and abs(two["delta"]) < 5
    assert two["text"].startswith("Plán byl dobrý, ztráta 1:0") and "vznikla při provedení: plánu ses držel" in two["text"]

    # the plan drawn again loses its numbers until the new line is priced; deleted, it has none and waits for none
    d = save(1, planned=[ll(*CONTROLS[0]), ll(*CONTROLS[1])]).get_json()
    assert d["legs"][0]["note"]["plan"] is None and d["plans_pending"]
    work(app)
    again = legs()["legs"][0]["note"]["plan"]
    assert abs(again["time"] - best[0]) / best[0] < 0.02 and again["text"] == "Plán byl dobrý a úsek jsi zaběhl bez ztráty."
    d = save(1, planned=None).get_json()
    assert d["legs"][0]["note"] == dict(planned=None, plan=None, deliberate_stop=False, lost_contact=False, green=None,
                                        fatigue=None, text="", corrected=None, control_desc="")
    assert not d["plans_pending"] and legs()["legs"][1]["note"]["plan"] == two

    # a new analysis of the race prices the plans again by itself (other routes, maybe another model)
    con.execute("UPDATE leg_notes SET plan = ? WHERE entry_id = ?", (json.dumps(dict(time=1)), entry))
    con.commit()
    clear_jobs(app)
    post(client, page + "/reanalyse")
    assert legs()["plans_pending"]
    work(app)
    assert [tuple(j) for j in con.execute("SELECT kind, status FROM jobs")] == [("analyse", "done")]
    assert legs()["legs"][1]["note"]["plan"] == two
    # without best routes there is nothing to price a plan with
    con.execute("UPDATE analyses SET has_routes = 0 WHERE entry_id = ?", (entry,))
    con.commit()
    d = save(3, planned=[ll(*CONTROLS[2]), ll(*CONTROLS[3])]).get_json()
    assert d["legs"][2]["note"]["plan"] is None and not d["plans_pending"]

    # somebody else cannot read the legs
    post(client, "/logout")
    register(client, "BFM0001")
    assert client.get(page + "/legs.json").status_code == 404


def test_old_database_gets_the_column_of_the_priced_plan(tmp_path):
    path = str(tmp_path / "app.db")
    con = dbm.connect(path)
    con.executescript("CREATE TABLE leg_notes (entry_id INTEGER NOT NULL, leg_n INTEGER NOT NULL, planned TEXT,"
                      " deliberate_stop INTEGER NOT NULL DEFAULT 0, lost_contact INTEGER NOT NULL DEFAULT 0, green TEXT,"
                      " fatigue INTEGER, text TEXT, updated_at TEXT NOT NULL DEFAULT (datetime('now')),"
                      " PRIMARY KEY (entry_id, leg_n));"
                      "INSERT INTO leg_notes (entry_id, leg_n, planned) VALUES (1, 1, '[]');")
    con.commit()
    dbm.init(path)
    assert tuple(con.execute("SELECT planned, plan FROM leg_notes").fetchone()) == ("[]", None)
