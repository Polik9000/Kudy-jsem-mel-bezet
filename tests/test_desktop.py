"""The app on one's own computer (desktop/app.py, OB_LOCAL=1): no login, no club site, the analysis scripts
started through the app itself when it is packaged."""
import os
import subprocess
import sys

import pytest
from conftest import FakeOris, csrf

from webapp import club
from webapp.config import ROOT


@pytest.fixture
def local(tmp_path, monkeypatch):
    monkeypatch.setenv("OB_LOCAL", "1")
    monkeypatch.setattr(club, "ENABLED", False)
    from webapp import create_app
    app = create_app(str(tmp_path / "instance"))
    app.config["TESTING"] = True
    app.config["OB"].oris_client = FakeOris()
    app.config["OB"].osm = False
    return app


def test_first_start_asks_for_regno_once(local):
    c = local.test_client()
    r = c.get("/")
    assert r.status_code == 302 and r.headers["Location"].endswith("/profile")
    assert "registrační číslo ORIS" in c.get("/profile").get_data(as_text=True)
    assert c.get("/").status_code == 200              # skipped: never asked again
    assert local.test_client().get("/").status_code == 200


def test_no_login(local):
    c = local.test_client()
    c.get("/")                                          # the first start goes to the profile
    r = c.get("/")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "Ukončit aplikaci" in html and "Odhlásit" not in html and "klubový web" not in html
    assert "číslo ORIS" in html          # the hint to give the number in the profile
    for page in ("/login", "/register", "/forgot"):
        assert c.get(page).status_code == 302
    profile = c.get("/profile").get_data(as_text=True)
    assert "Změna hesla" not in profile and "Zrušení účtu" not in profile and "nikam se neposílají" in profile


def test_one_runner(local):
    c = local.test_client()
    c.get("/")
    c.get("/profile")
    from webapp import db as dbm
    con = dbm.connect(local.config["OB"].db_path)
    assert con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1


def test_regno_once_in_profile(local):
    c = local.test_client()
    r = c.post("/profile", data=dict(csrf_token=csrf(c, "/profile"), name="", oris_regno="bfm0903"))
    assert r.status_code == 302
    from webapp import db as dbm
    con = dbm.connect(local.config["OB"].db_path)
    u = con.execute("SELECT * FROM users").fetchone()
    assert u["oris_regno"] == "BFM0903" and u["oris_user_id"] == 45118 and u["name"]
    assert con.execute("SELECT kind FROM jobs").fetchone()["kind"] == "sync_oris"
    # given once: another number is not taken any more
    c.post("/profile", data=dict(csrf_token=csrf(c, "/profile"), name="X", oris_regno="BFM0001"))
    assert con.execute("SELECT oris_regno FROM users").fetchone()[0] == "BFM0903"


def test_unknown_regno(local):
    c = local.test_client()
    r = c.post("/profile", data=dict(csrf_token=csrf(c, "/profile"), oris_regno="XYZ9999"), follow_redirects=True)
    assert "v ORIS není" in r.get_data(as_text=True)


def test_quit(local):
    c = local.test_client()
    assert c.post("/konec", data=dict(csrf_token=csrf(c, "/profile"))).status_code == 404   # no window to close
    called = []
    local.config["OB_QUIT"] = lambda: called.append(1)
    r = c.post("/konec", data=dict(csrf_token=csrf(c, "/profile")))
    assert r.status_code == 200 and called == [1]


def test_quit_not_on_the_server(app, user):
    c = app.test_client()
    app.config["OB_QUIT"] = lambda: None
    with c.session_transaction() as s:
        s["user_id"] = user
    assert c.post("/konec", data=dict(csrf_token=csrf(c, "/profile"))).status_code == 404


def test_data_dir(monkeypatch, tmp_path):
    from desktop import app as desktop
    monkeypatch.setenv("OB_INSTANCE", str(tmp_path))
    assert desktop.data_dir() == str(tmp_path)
    monkeypatch.delenv("OB_INSTANCE")
    assert desktop.data_dir().endswith(desktop.APP_FOLDER)


@pytest.mark.parametrize("args, out", [(["-u", "-m", "oroute.slopefit", "--help"], "slope_prior"),
                                       (["-u", "analyze.py", "--help"], "usage")])
def test_as_python(args, out):
    """What the packaged app does when the web layer starts a script with it (runner._run)."""
    code = ("import sys; from desktop import app; app.as_python(sys.argv[1:]); print('not a script')")
    p = subprocess.run([sys.executable, "-c", code, *args], cwd=ROOT, capture_output=True, text=True, timeout=120,
                       env=dict(os.environ, PYTHONPATH=ROOT))
    assert p.returncode == 0, p.stderr
    assert out in p.stdout and "not a script" not in p.stdout


def test_as_python_other():
    from desktop import app as desktop
    assert desktop.as_python(["--browser"]) is False and desktop.as_python([]) is False


def test_data_page_shows_version_folder_and_release_link(local):
    from webapp import VERSION
    c = local.test_client()
    html = c.get("/profile").get_data(as_text=True)
    assert VERSION in html and local.config["OB"].instance in html
    assert "Otevřít složku s daty" in html and "Smazat všechna moje data" in html
    assert "github.com/Polik9000/Kudy-jsem-mel-bezet/releases/latest" in html


def test_open_folder_asks_the_system(local, monkeypatch):
    from webapp.services import local_data
    seen = []
    monkeypatch.setattr(local_data, "open_folder", lambda p: seen.append(p) or True)
    c = local.test_client()
    r = c.post("/data/slozka", data=dict(csrf_token=csrf(c, "/profile")))
    assert r.status_code == 302 and seen == [local.config["OB"].instance]


def test_wipe_needs_the_word_and_deletes_everything(local):
    from fitfile import fit_bytes

    from webapp import db as dbm
    from webapp.services import storage
    conf = local.config["OB"]
    c = local.test_client()
    c.get("/")
    con = dbm.connect(conf.db_path)
    uid = con.execute("SELECT id FROM users").fetchone()["id"]
    storage.save_activity(con, conf, uid, fit_bytes([(t, 50.0 + t * 1e-5, 18.0) for t in range(0, 600, 2)]), "r.fit", "fit")
    ev = con.execute("INSERT INTO events (name, date) VALUES ('X', '2026-01-01')").lastrowid
    cid = con.execute("INSERT INTO classes (event_id, name) VALUES (?, 'H')", (ev,)).lastrowid
    con.execute("INSERT INTO entries (user_id, class_id) VALUES (?, ?)", (uid, cid))
    con.commit()
    assert os.path.isdir(conf.path("fit"))
    # without the word nothing goes
    r = c.post("/data/smazat", data=dict(csrf_token=csrf(c, "/profile"), potvrzeni="ano"))
    assert r.status_code == 302 and con.execute("SELECT COUNT(*) FROM entries").fetchone()[0] == 1
    assert os.path.isdir(conf.path("fit"))
    # a running job holds it back
    con.execute("INSERT INTO jobs (kind, user_id, status) VALUES ('analyse', ?, 'running')", (uid,))
    con.commit()
    c.post("/data/smazat", data=dict(csrf_token=csrf(c, "/profile"), potvrzeni="SMAZAT"))
    assert con.execute("SELECT COUNT(*) FROM entries").fetchone()[0] == 1
    con.execute("DELETE FROM jobs")
    con.commit()
    r = c.post("/data/smazat", data=dict(csrf_token=csrf(c, "/profile"), potvrzeni="SMAZAT"))
    assert r.status_code == 302
    assert not os.path.exists(conf.path("fit"))
    for t in ("events", "classes", "entries", "activities"):
        assert con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0
    assert c.get("/", follow_redirects=True).status_code == 200   # the app goes on, with a fresh runner


def test_data_buttons_do_not_exist_on_the_server(app, client, user):
    assert client.post("/data/smazat", data=dict(csrf_token=csrf(client, "/"), potvrzeni="SMAZAT")).status_code == 404
    assert client.post("/data/slozka", data=dict(csrf_token=csrf(client, "/"))).status_code == 404


def test_new_version_opens_the_database_of_an_old_one(tmp_path, monkeypatch):
    """The update installs over the old app: the data folder is the same, an old database loses nothing."""
    import sqlite3

    from webapp import create_app
    from webapp import db as dbm
    monkeypatch.setenv("OB_LOCAL", "1")
    first = create_app(str(tmp_path / "data"))
    con = dbm.connect(first.config["OB"].db_path)
    ev = con.execute("INSERT INTO events (name, date) VALUES ('Starý závod', '2025-05-17')").lastrowid
    cid = con.execute("INSERT INTO classes (event_id, name) VALUES (?, 'H')", (ev,)).lastrowid
    con.commit()
    first.test_client().get("/")
    uid = con.execute("SELECT id FROM users").fetchone()["id"]
    con.execute("INSERT INTO entries (user_id, class_id) VALUES (?, ?)", (uid, cid))
    con.commit()
    con.close()
    # an older version had fewer columns
    old = sqlite3.connect(first.config["OB"].db_path)
    old.execute("ALTER TABLE entries DROP COLUMN own_osm_mode")
    old.execute("ALTER TABLE events DROP COLUMN maponly_acc_m")
    old.commit()
    old.close()
    second = create_app(str(tmp_path / "data"))
    html = second.test_client().get("/").get_data(as_text=True)
    assert "Starý závod" in html


def test_script_survives_a_closed_pipe_and_closing_the_app_ends_scripts():
    """The app was closed while a calculation ran: its print into the lost pipe (OSError 22 on Windows) must not
    end the calculation, and kill_all ends the scripts that are still running."""
    import subprocess
    import sys

    from desktop import app as desktop_app
    from webapp.services import runner

    class Lost:
        def write(self, text):
            raise OSError(22, "Invalid argument")

        def flush(self):
            raise OSError(22, "Invalid argument")
    t = desktop_app._Tolerant(Lost())
    assert t.write("abc") == 3
    t.flush()
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    runner._RUNNING.add(p)
    runner.kill_all()
    assert p.wait(10) != 0
    runner._RUNNING.discard(p)


def test_external_links_open_in_the_system_browser(local, monkeypatch):
    """The app window has no address bar: ORIS and other sites open in the browser (POST, with the token)."""
    import webbrowser
    opened = []
    monkeypatch.setattr(webbrowser, "open", lambda url: opened.append(url))
    cl = local.test_client()
    html = cl.get("/", follow_redirects=True).get_data(as_text=True)
    import re
    assert 'external: "/externi"' in html
    tok = re.search(r'csrf: "([0-9a-f]+)"', html).group(1)
    r = cl.post("/externi", json={"url": "https://oris.ceskyorientak.cz/"}, headers={"X-CSRF-Token": tok})
    assert r.status_code == 204 and opened == ["https://oris.ceskyorientak.cz/"]
    for bad in ("file:///etc/passwd", "javascript:alert(1)", "", "oris"):
        assert cl.post("/externi", json={"url": bad}, headers={"X-CSRF-Token": tok}).status_code == 400
    assert cl.post("/externi", json={"url": "https://x.cz"}).status_code in (400, 403)
    assert opened == ["https://oris.ceskyorientak.cz/"]
