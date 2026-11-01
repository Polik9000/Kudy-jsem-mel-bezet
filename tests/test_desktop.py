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


def test_no_login(local):
    c = local.test_client()
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
    assert c.post("/konec", data=dict(csrf_token=csrf(c, "/"))).status_code == 404   # no window to close
    called = []
    local.config["OB_QUIT"] = lambda: called.append(1)
    r = c.post("/konec", data=dict(csrf_token=csrf(c, "/")))
    assert r.status_code == 200 and called == [1]


def test_quit_not_on_the_server(app, user):
    c = app.test_client()
    app.config["OB_QUIT"] = lambda: None
    with c.session_transaction() as s:
        s["user_id"] = user
    assert c.post("/konec", data=dict(csrf_token=csrf(c, "/"))).status_code == 404


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
