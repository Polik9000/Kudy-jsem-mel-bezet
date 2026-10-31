"""Stopping jobs (services/jobs.stop): a waiting one at once, a running one with its script killed, only one's own,
and nothing half written left behind (runner._staged)."""
import json
import os
import threading
import time

import pytest
from conftest import post, register
from test_recompute import _fake_refit, _scripts
from test_web_races import con_of, work

from webapp import db as dbm
from webapp.seed import seed_demo
from webapp.services import jobs, personal, runner


def _stop_later(app, job_kind, user, after=1.0):
    """From another connection (as the web process would), stop the user's running job of this kind."""
    def go():
        time.sleep(after)
        con = dbm.connect(app.config["OB"].db_path)
        for _ in range(100):
            row = con.execute("SELECT id FROM jobs WHERE kind = ? AND status = 'running'", (job_kind,)).fetchone()
            if row:
                jobs.stop(con, row["id"], user)
                break
            time.sleep(0.1)
        con.close()
    t = threading.Thread(target=go)
    t.start()
    return t


def test_waiting_job_stops_at_once_and_only_its_owner_can(app, client, user):
    con = con_of(app)
    mine = jobs.enqueue(con, "refit_model", user_id=user)
    other = con.execute("INSERT INTO users (username, password_hash) VALUES ('jiny', '-')").lastrowid
    theirs = jobs.enqueue(con, "refit_model", user_id=other)
    html = client.get("/jobs").get_data(as_text=True)
    assert "Zastavit všechny moje" in html and f"/jobs/{mine}/stop" in html and f"/jobs/{theirs}/stop" not in html
    assert post(client, f"/jobs/{theirs}/stop").status_code == 404
    assert con.execute("SELECT status FROM jobs WHERE id = ?", (theirs,)).fetchone()[0] == "queued"
    assert post(client, f"/jobs/{mine}/stop").status_code == 302
    row = con.execute("SELECT status, stop_requested FROM jobs WHERE id = ?", (mine,)).fetchone()
    assert tuple(row) == ("stopped", 1)
    assert "zastaveno" in client.get("/jobs").get_data(as_text=True)
    # the worker does not take it; the other runner's job still runs
    work(app)
    assert con.execute("SELECT status FROM jobs WHERE id = ?", (mine,)).fetchone()[0] == "stopped"
    assert con.execute("SELECT status FROM jobs WHERE id = ?", (theirs,)).fetchone()[0] == "done"
    # stopping all: only the runner's own
    a = jobs.enqueue(con, "refit_model", user_id=user)
    b = jobs.enqueue(con, "sync_oris", user_id=user)
    c = jobs.enqueue(con, "refit_model", user_id=other)
    post(client, "/jobs/stop")
    st = {r["id"]: r["status"] for r in con.execute("SELECT id, status FROM jobs")}
    assert st[a] == st[b] == "stopped" and st[c] == "queued"
    # somebody else cannot stop the runner's jobs either
    d = jobs.enqueue(con, "refit_model", user_id=user)
    post(client, "/logout")
    register(client, "BFM0001")
    assert post(client, f"/jobs/{d}/stop").status_code == 404
    post(client, "/jobs/stop")
    assert con.execute("SELECT status FROM jobs WHERE id = ?", (d,)).fetchone()[0] == "queued"


@pytest.mark.needs_data
def test_running_analysis_is_killed_and_the_finished_one_stays(app, client, user, monkeypatch):
    con, conf = con_of(app), app.config["OB"]
    entry = seed_demo(con, conf, user)["pohora"]
    con.execute("DELETE FROM jobs WHERE entry_id IS NOT ?", (entry,))
    con.commit()
    log, news = [], [True]
    fake = _scripts(log)
    real_run = runner._run
    monkeypatch.setattr(runner, "_run", fake)
    monkeypatch.setattr(personal, "refit", _fake_refit(log, news))
    work(app)                                            # a finished analysis with routes
    folder = conf.path("races", f"entry_{entry}")
    with open(os.path.join(folder, "best", "best.json")) as f:
        before = f.read()
    aid = con.execute("SELECT id FROM analyses WHERE entry_id = ?", (entry,)).fetchone()[0]

    def slow(*cmd, on_line=None):
        if cmd[0] == "bestroute.py" and "--samples-only" not in cmd:
            with open(os.path.join(cmd[4], "best.json"), "w") as f:     # half of a new result ...
                f.write("{half")
            real_run("-c", "import time; time.sleep(60)")              # ... and a script that takes long
        return fake(*cmd, on_line=on_line)
    monkeypatch.setattr(runner, "_run", slow)
    post(client, f"/races/{entry}/reanalyse")
    t0 = time.time()
    stopper = _stop_later(app, "analyse", user)
    work(app)
    stopper.join()
    assert time.time() - t0 < 30                                      # the script was killed, not waited for
    job = con.execute("SELECT * FROM jobs WHERE kind = 'analyse' ORDER BY id DESC").fetchone()
    assert job["status"] == "stopped" and job["message"].startswith("Zastaveno.")
    assert not con.execute("SELECT 1 FROM jobs WHERE status = 'running'").fetchone()
    with open(os.path.join(folder, "best", "best.json")) as f:
        assert f.read() == before                                    # the last finished analysis is valid
    assert con.execute("SELECT id FROM analyses WHERE entry_id = ?", (entry,)).fetchone()[0] == aid
    assert not os.path.exists(folder + ".new") and not os.path.exists(folder + ".old")
    page = client.get(f"/races/{entry}").get_data(as_text=True)
    assert "Poslední analýzu jsi zastavil. Platí rozbor, který byl hotový před ní." in page


@pytest.mark.needs_data
def test_stopped_recompute_all_keeps_the_races_it_finished(app, client, user, monkeypatch):
    con, conf = con_of(app), app.config["OB"]
    entries = seed_demo(con, conf, user)
    log, news = [], [True]
    fake = _scripts(log)
    real_run = runner._run
    monkeypatch.setattr(runner, "_run", fake)
    monkeypatch.setattr(personal, "refit", _fake_refit(log, news))
    work(app)
    routed = []

    def slow(*cmd, on_line=None):
        if cmd[0] == "bestroute.py" and "--samples-only" not in cmd:
            routed.append(cmd[4])
            if len(routed) == 2:                                     # the second race takes long
                real_run("-c", "import time; time.sleep(60)")
        return fake(*cmd, on_line=on_line)
    monkeypatch.setattr(runner, "_run", slow)
    jobs.enqueue(con, "recompute_all", user_id=user)
    stopper = _stop_later(app, "recompute_all", user)
    work(app)
    stopper.join()
    job = con.execute("SELECT * FROM jobs WHERE kind = 'recompute_all'").fetchone()
    assert job["status"] == "stopped"
    model = runner.current_model(con, user)["id"]
    on = {r["entry_id"]: r["model_id"] for r in con.execute("SELECT entry_id, model_id FROM analyses")}
    assert sum(m == model for m in on.values()) == 1                  # the first race is done with the new model
    stale = [e for e, m in on.items() if m != model]
    assert len(stale) == 3
    assert "Postupy jsou spočítané se starším modelem rychlosti." in client.get(f"/races/{stale[0]}").get_data(as_text=True)
    assert not [d for d in os.listdir(conf.path("races")) if d.endswith((".new", ".old"))]
    assert set(on) == set(entries.values())


def test_worker_restart_does_not_leave_a_stopped_job_running(app):
    con = con_of(app)
    con.execute("INSERT INTO jobs (kind, status, started_at, stop_requested) VALUES"
                " ('analyse', 'running', datetime('now', '-1 hour'), 1),"
                " ('analyse', 'running', datetime('now', '-1 hour'), 0)")
    con.commit()
    jobs.requeue_interrupted(con)
    assert [r[0] for r in con.execute("SELECT status FROM jobs ORDER BY id")] == ["stopped", "queued"]


def test_samples_written_whole(tmp_path):
    """official.json and the like are written whole or not at all (runner._write_json)."""
    path = str(tmp_path / "x.json")
    runner._write_json(path, dict(a=1))
    assert json.load(open(path)) == dict(a=1) and os.listdir(tmp_path) == ["x.json"]
