"""The route of an average runner in the web app (bestroute.py --generic, oroute/generic.py): stored with the
leg, on the leg panel and its table, left out of the answers without geometry, counted on the model page."""
import io
import json
import os

from conftest import csrf, post
from races import inputs
from test_web_plans import CONTROLS, flat_elevation, made_up_map, scripts, work

from oroute.speedmodel import SpeedModel
from webapp import db as dbm
from webapp.services import personal, runner

SENTENCE = ("Běžec s průměrným modelem by kopec obíhal vpravo; tobě by ten postup trval 2:41. Pro tebe je "
            "rychlejší přes kopec (2:29), protože do kopce běžíš o 18 % rychleji než průměr.")


def with_average(run, seen):
    """bestroute.py of test_web_plans, plus the average runner on leg 1-2 (differs) and S-1 (the same)."""
    def wrapped(*cmd, on_line=None):
        out = run(*cmd, on_line=on_line)
        if cmd and cmd[0] == "bestroute.py" and "--samples-only" not in cmd:
            seen.append(cmd)
            path = os.path.join(cmd[4], "best.json")
            with open(path) as f:
                best = json.load(f)
            legs = best["legs"]
            legs[1]["generic"] = dict(differs=True, apart=0.6, time=161.0, time_avg=150.0, gain=12.0, dist=420.0,
                                      climb=4.0, side="right", text_cs=SENTENCE, text_en="...",
                                      reason=dict(kind="up", cls=None, pct=0.18, weight=20.0),
                                      route=[[49.6, 18.3], [49.601, 18.301], [49.6, 18.302]])
            legs[0]["generic"] = dict(differs=False, apart=0.0, time=legs[0]["best"]["time"], gain=0.0,
                                      time_avg=1.0, dist=1.0, climb=0.0, side=None, reason=None, route=None,
                                      text_cs="Tady by stejně běžel každý.", text_en="Any runner ...")
            with open(path, "w") as f:
                json.dump(best, f)
        return out
    return wrapped


def test_average_runner_is_stored_shown_and_counted(app, client, user, monkeypatch):
    con, conf = dbm.connect(app.config["OB"].db_path), app.config["OB"]
    page = post(client, "/races/new", name="Trénink na louce", date="2026-03-28", class_name="T").headers["Location"]
    entry = int(page.rsplit("/", 1)[1])
    kmz, gm = made_up_map()
    with open(inputs("pohora")[2], "rb") as fit:
        client.post(page + "/files", content_type="multipart/form-data", data=dict(
            csrf_token=csrf(client), fit=(fit, "run.fit"), course=(io.BytesIO(kmz), "course.kmz"),
            maponly=(io.BytesIO(kmz), "maponly.kmz")))
    event = con.execute("SELECT c.event_id FROM entries e JOIN classes c ON c.id = e.class_id").fetchone()[0]
    flat_elevation(conf.path("dem", f"event_{event}.npz"), gm)
    seen = []
    monkeypatch.setattr(runner, "_run", with_average(scripts(gm, [100.0] * (len(CONTROLS) - 1)), seen))
    monkeypatch.setattr(personal, "refit", lambda con, conf, uid, fresh=None: (None, False))
    work(app)
    # no Garmin export of the runner: their slope is the default one, only the terrain is compared
    assert seen and seen[-1][seen[-1].index("--generic") + 1] == "terrain"

    legs = client.get(page + "/data.json").get_json()["legs"]
    assert legs[1]["generic"]["text_cs"] == SENTENCE and legs[1]["generic"]["route"]
    assert legs[0]["generic"]["differs"] is False and legs[2]["generic"] is None
    light = client.get(page + "/legs.json").get_json()["legs"]       # numbers only: the routes stay on the page
    assert "route" not in light[1]["generic"] and light[1]["generic"]["text_cs"] == SENTENCE
    html = client.get(page).get_data(as_text=True)
    assert 'id="p-pro-tebe"' in html and 'id="c-prumer"' in html and "průměrný běžec" in html

    uid = con.execute("SELECT user_id FROM entries WHERE id = ?", (entry,)).fetchone()[0]
    os.makedirs(conf.path("models"), exist_ok=True)
    m = SpeedModel(notes=dict(personal=dict(half_life_days=365, races=[])))
    m.save(conf.path("models", "test.json"))
    con.execute("INSERT INTO speed_models (user_id, model, file) VALUES (?, ?, ?)",
                (uid, json.dumps(m.to_dict()), os.path.join("models", "test.json")))
    con.commit()
    html = client.get("/model").get_data(as_text=True)
    assert "Proti průměrnému běžci" in html
    assert "Na <b>1</b> z 2 úseků (50 %,\n  1 závod)" in html, html[html.index("Proti průměrnému"):][:600]
    assert "do kopce jsi rychlejší než průměr (1×)" in html
    assert f"#usek-2\">Trénink na louce, úsek {legs[1]['name']}</a>" in html and SENTENCE in html
