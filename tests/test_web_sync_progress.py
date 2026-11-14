"""Loading the races from ORIS can be seen: the race list says it is loading and how far, the button is off
meanwhile, and the result shows when it is done (issue 1). ORIS answers from tests/fixtures/oris."""
from conftest import csrf, post

from webapp import db as dbm
from webapp.services import sync_oris


def con_of(app):
    return dbm.connect(app.config["OB"].db_path)


def _job(app, user, status, message=None, finished="datetime('now')"):
    con = con_of(app)
    jid = con.execute(f"INSERT INTO jobs (kind, user_id, status, message, finished_at) VALUES ('sync_oris', ?, ?, ?,"
                      f" {finished if status in ('done', 'failed') else 'NULL'})", (user, status, message)).lastrowid
    con.commit()
    return jid


def test_waiting_load_is_shown_and_the_button_is_off(app, client, user):
    jid = _job(app, user, "queued")
    html = client.get("/").get_data(as_text=True)
    assert "Načítám závody z ORIS" in html and f'data-ceka-na="{jid}"' in html and "čeká ve frontě" in html
    button = html[html.index('action="/sync"'):]
    button = button[:button.index("</button>")]
    assert " disabled" in button


def test_running_load_says_how_far(app, client, user):
    _job(app, user, "running", "zatím 12 z 85 závodů")
    html = client.get("/").get_data(as_text=True)
    assert "Načítám závody z ORIS" in html and "zatím 12 z 85 závodů" in html


def test_no_second_load_while_one_runs(app, client, user):
    _job(app, user, "running")
    post(client, "/sync")
    con = con_of(app)
    assert con.execute("SELECT COUNT(*) FROM jobs WHERE kind = 'sync_oris'").fetchone()[0] == 1


def test_result_shows_when_done(app, client, user):
    _job(app, user, "done", "ORIS: 3 závodů (3 nových), oficiální čas doplněn u 2.")
    html = client.get("/").get_data(as_text=True)
    assert "Načítám závody z ORIS" not in html and "Načteno z ORIS. ORIS: 3 závodů" in html
    button = html[html.index('action="/sync"'):]
    assert " disabled" not in button[:button.index("</button>")]


def test_old_result_is_not_repeated(app, client, user):
    _job(app, user, "done", "ORIS: 3 závodů", finished="datetime('now', '-2 hours')")
    assert "Načteno z ORIS" not in client.get("/").get_data(as_text=True)


def test_jobs_json_lists_the_waiting_jobs(app, client, user):
    jid = _job(app, user, "queued")
    d = client.get("/jobs.json").get_json()
    assert d["ids"] == [jid] and d["active"] == 1


def test_sync_says_how_far(app, user):
    said = []
    con = con_of(app)
    sync_oris.sync_user(con, app.config["OB"], user, pause=0, progress=said.append)
    n = len(app.config["OB"].oris_client.entries(45118))
    assert said[0] == f"zatím 0 z {n} závodů" and said[-1] == f"zatím {n} z {n} závodů" and len(said) == n + 1


def test_sync_job_reports_its_progress(app, user, monkeypatch):
    from webapp import worker
    from webapp.services import jobs, sync_oris

    monkeypatch.setattr(sync_oris, "PAUSE_S", 0)
    monkeypatch.setattr(sync_oris.sync_user, "__defaults__", (None, None, 0, True, None))
    con = con_of(app)
    jid = jobs.enqueue(con, "sync_oris", user_id=user)
    texts, real = [], jobs.progress
    monkeypatch.setattr(jobs, "progress", lambda c, j, text: texts.append((j, text)) or real(c, j, text))
    worker.load_handlers()
    assert worker.run_once(app.config["OB"]) == 1
    assert texts and all(j == jid for j, _t in texts) and texts[-1][1].startswith("zatím")
    assert con.execute("SELECT status FROM jobs WHERE id = ?", (jid,)).fetchone()[0] == "done"


def test_profile_says_the_load_takes_a_while(tmp_path, monkeypatch):
    from conftest import FakeOris

    from webapp import club, create_app
    monkeypatch.setenv("OB_LOCAL", "1")
    monkeypatch.setattr(club, "ENABLED", False)
    app = create_app(str(tmp_path / "instance"))
    app.config["TESTING"] = True
    app.config["OB"].oris_client = FakeOris()
    c = app.test_client()
    html = c.get("/profile").get_data(as_text=True)
    assert "Po uložení se z ORIS načtou všechny tvoje závody" in html and "několik" in html
    r = c.post("/profile", data=dict(csrf_token=csrf(c, "/profile"), name="", oris_regno="BFM0903"),
               follow_redirects=True)
    html = r.get_data(as_text=True)
    assert "načítají všechny tvoje závody" in html and "Načítám závody z ORIS" in html   # straight on the race list
