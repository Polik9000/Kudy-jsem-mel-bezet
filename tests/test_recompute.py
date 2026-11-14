"""„Přepočítat všechno“ (handlers._recompute_all): samples of every race, one model, then the routes of every race
with that model, and nothing at all when nothing has changed."""
import json
import os

from conftest import post
from test_web_races import con_of, work

from oroute import course as course_mod
from oroute.speedmodel import SpeedModel
from webapp.seed import seed_demo
from webapp.services import jobs, personal, results, runner


def _scripts(log):
    """Stand-in for runner._run: what analyze.py, bestroute.py and relocate.py leave behind (three legs, current
    versions), noting in `log` what ran."""
    route = dict(time=60.0, dist=200.0, climb=5.0, mix={})

    def run(*cmd, on_line=None):
        if cmd[:2] == ("-m", "oroute.hatch"):
            with open(cmd[3], "w") as f:
                json.dump(dict(areas=[]), f)
        elif cmd[:2] == ("-m", "oroute.relocate"):
            log.append(("relocate",))
            with open(cmd[4], "w") as f:
                json.dump(dict(version=results.RELOCATE, controls=[]), f)
        elif cmd[0] == "analyze.py":
            log.append(("analyze",))
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
                               legs=legs, course_version=course_mod.VERSION), f)
        elif "--samples-only" in cmd:
            log.append(("samples", os.path.basename(os.path.dirname(cmd[4]))))
            open(os.path.join(cmd[4], "leg_samples.npz"), "wb").close()
        else:
            log.append(("routes", os.path.basename(os.path.dirname(cmd[4])), cmd[cmd.index("--model") + 1]))
            open(os.path.join(cmd[4], "leg_samples.npz"), "wb").close()
            with open(os.path.join(cmd[4], "best.json"), "w") as f:
                json.dump(dict(version=results.ROUTES, dem="aws", barriers=None, legs=[
                    dict(leg=k, best=route, yours=route, straight=route, route=[[49.6, 18.3], [49.6, 18.3]],
                         text_cs="rovně", text_en="straight") for k in (1, 2, 3)]), f)
    return run


def _fake_refit(log, news):
    """Stand-in for personal.refit: a new model only while news[0] is True (the data changed), else the last one."""
    def refit(con, conf, uid, today=None, fresh=None, tol=0.0):
        log.append(("refit", fresh))
        last = runner.current_model(con, uid)
        if last is not None and not news[0]:
            return last["id"], False
        rel = f"models/m{len(log)}.json"
        model = SpeedModel()
        model.notes["personal"] = dict(races=[], half_life_days=365.0)
        os.makedirs(conf.path("models"), exist_ok=True)
        model.save(conf.path(rel))
        mid = con.execute("INSERT INTO speed_models (user_id, model, file) VALUES (?, ?, ?)",
                          (uid, json.dumps(model.to_dict()), rel)).lastrowid
        con.commit()
        return mid, True
    return refit


def _models(con):
    return {r["entry_id"]: r["model_id"] for r in con.execute("SELECT entry_id, model_id FROM analyses")}


def test_recompute_all_uses_one_model_and_does_nothing_twice(app, client, user, monkeypatch):
    con, conf = con_of(app), app.config["OB"]
    entries = seed_demo(con, conf, user)
    log, news = [], [True]
    monkeypatch.setattr(runner, "_run", _scripts(log))
    monkeypatch.setattr(personal, "refit", _fake_refit(log, news))
    work(app)                                       # the four analyses, each refits the model before its routes
    first = _models(con)
    assert len(first) == 4 and len(set(first.values())) == 4      # every race was drawn with another model

    # the model changes once more (a note, say): one run puts every race on one model, refitting once
    del log[:]
    post(client, "/model/prepocitat-vse", zpet="/races/")
    assert con.execute("SELECT COUNT(*) FROM jobs WHERE kind = 'recompute_all' AND status = 'queued'").fetchone()[0] == 1
    work(app)
    job = con.execute("SELECT * FROM jobs WHERE kind = 'recompute_all'").fetchone()
    assert job["status"] == "done", job["error"]
    assert job["message"].startswith("Přepočítáno 4 z 4 závodů s jedním modelem (model se změnil)")
    model = runner.current_model(con, user)
    assert set(_models(con).values()) == {model["id"]}
    assert [x for x in log if x[0] == "refit"] == [("refit", None)]          # once, between steps 1 and 3
    assert not [x for x in log if x[0] in ("samples", "analyze")]            # the samples were current
    routes = [x for x in log if x[0] == "routes"]
    assert len(routes) == 4 and {x[2] for x in routes} == {conf.path(model["file"])}
    # step 3 found the routes after the refit, never before it
    assert log.index(("refit", None)) < log.index(routes[0])

    # nothing changed: nothing is computed and no model is added
    del log[:]
    news[0] = False
    n_models = con.execute("SELECT COUNT(*) FROM speed_models").fetchone()[0]
    jobs.enqueue(con, "recompute_all", user_id=user)
    work(app)
    job = con.execute("SELECT * FROM jobs WHERE kind = 'recompute_all' ORDER BY id DESC").fetchone()
    assert job["message"].startswith("Nic nového: všechny 4 závody už mají"), job["message"]
    assert [x[0] for x in log] == ["refit"]
    assert con.execute("SELECT COUNT(*) FROM speed_models").fetchone()[0] == n_models

    # the samples of one race were read with older code: only that one is read again, and its routes found again
    del log[:]
    one = entries["petrvald"]
    os.remove(conf.path("races", f"entry_{one}", "best", "samples.json"))
    jobs.enqueue(con, "recompute_all", user_id=user)
    work(app)
    # (each written in a copy of the folder that replaces it when it is whole)
    assert [x[:2] for x in log if x[0] in ("samples", "routes")] == [("samples", f"entry_{one}.new"),
                                                                      ("routes", f"entry_{one}.new")]
    assert not os.path.exists(conf.path("races", f"entry_{one}.new"))
    assert os.path.exists(conf.path("races", f"entry_{one}", "best", "samples.json"))
    assert set(_models(con).values()) == {model["id"]}

    # the course of one race was read from the map by older code (a newer bestroute.VERSION goes with it): the
    # course of that one is read again, the others only get their routes
    del log[:]
    path = conf.path("races", f"entry_{one}", "analysis.json")
    with open(path, encoding="utf-8") as f:
        A = json.load(f)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dict(A, course_version=0), f)
    con.execute("UPDATE analyses SET summary = json_set(summary, '$.routes', 1)")
    con.commit()
    jobs.enqueue(con, "recompute_all", user_id=user)
    work(app)
    assert [x for x in log if x[0] == "analyze"] == [("analyze",)]
    assert len([x for x in log if x[0] == "routes"]) == 4


def test_recompute_all_shows_progress_by_race(app, client, user, monkeypatch):
    con, conf = con_of(app), app.config["OB"]
    seed_demo(con, conf, user)
    log, news = [], [True]
    monkeypatch.setattr(runner, "_run", _scripts(log))
    monkeypatch.setattr(personal, "refit", _fake_refit(log, news))
    work(app)
    said = []
    real = jobs.progress
    monkeypatch.setattr(jobs, "progress", lambda con, job_id, text: said.append(text) or real(con, job_id, text))
    jobs.enqueue(con, "recompute_all", user_id=user)
    work(app)
    assert any(t.startswith("vzorky 1 z 4 závodů") for t in said), said
    assert "přepočítávám osobní model" in said
    assert any(t.startswith("postupy 3 z 4 závodů") for t in said), said


def test_model_page_and_race_list_offer_recompute_all(app, client, user, monkeypatch):
    con, conf = con_of(app), app.config["OB"]
    entries = seed_demo(con, conf, user)
    log, news = [], [True]
    monkeypatch.setattr(runner, "_run", _scripts(log))
    monkeypatch.setattr(personal, "refit", _fake_refit(log, news))
    work(app)
    html = client.get("/model").get_data(as_text=True)
    assert "Model se učí z tvých stop ve všech závodech" in html and "Přepočítat všechno" in html
    assert "Přepočítat všechno" in client.get("/").get_data(as_text=True)
    # the first race was drawn with an older model than the latest
    page = client.get(f"/races/{entries['pohora']}").get_data(as_text=True)
    assert "Postupy jsou spočítané se starším modelem rychlosti." in page
    r = post(client, "/model/prepocitat-vse", zpet="//jinam.example")
    assert r.status_code == 302 and r.headers["Location"].endswith("/model")


def test_refit_keeps_a_model_that_is_nearly_the_same():
    a = dict(v_flat=3.000, up_k=4.0, factors={"forest": 0.8, "path": 1.0})
    b = dict(v_flat=3.010, up_k=4.0, factors={"forest": 0.801, "path": 1.0})
    assert not personal._same(a, b) and personal._same(a, b, personal.KEEP_TOL)
    c = dict(b, v_flat=3.05)
    assert not personal._same(a, c, personal.KEEP_TOL)
