"""Runs straight from Garmin Connect (Personal API, webapp/services/garmin_api.py), against a fake Garmin:
the key stays in the data folder, the token is cached and renewed, activities are offered, downloaded,
stored and paired; only the app on one's own computer has the page."""
import base64
import datetime as dt
import io
import json
import os
import re
import time
import zipfile

import pytest
from conftest import FakeOris, csrf
from fitfile import fit_bytes

from webapp import club
from webapp.services import garmin_api
from webapp.worker import load_handlers, run_once

KEY = "pk_test_0123456789abcdef0123456789"


def _jwt(exp):
    def b64(o):
        return base64.urlsafe_b64encode(json.dumps(o).encode()).decode().rstrip("=")
    return f"{b64({'alg': 'none'})}.{b64({'exp': exp})}.sig"


def _zip(name, data):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(name, data)
    return buf.getvalue()


class FakeGarmin:
    """Answers as personal.connectapi.garmin.com would. acts: {id: (start UTC, typeKey)}."""

    def __init__(self, acts):
        self.acts, self.calls, self.tokens, self.reject_token = acts, [], 0, False

    def __call__(self, method, url, headers):
        path = url.split("connectapi.garmin.com", 1)[1]
        self.calls.append((method, path))
        if path == garmin_api.TOKEN_PATH:
            assert method == "POST"
            if self.reject_token or headers["Authorization"] != f"ApiKey {KEY}":
                return 401, b"invalid key"
            self.tokens += 1
            return 200, _jwt(time.time() + 86400).encode()
        assert headers["Authorization"].startswith("Bearer ")
        if path.startswith(garmin_api.LIST_PATH):
            q = dict(p.split("=") for p in path.split("?", 1)[1].split("&"))
            since = dt.date.fromisoformat(q["startDate"]) if "startDate" in q else dt.date.min
            rows = [dict(activityId=i, activityName=f"Běh {i}", startTimeGMT=s.strftime("%Y-%m-%d %H:%M:%S"),
                         activityType=dict(typeKey=t), distance=5000.0, duration=1800.0)
                    for i, (s, t) in sorted(self.acts.items(), key=lambda x: x[1][0], reverse=True) if s.date() >= since]
            start, limit = int(q["start"]), int(q["limit"])
            return 200, json.dumps(rows[start:start + limit]).encode()
        if path.startswith("/download-service/files/activity/"):
            i = int(path.rsplit("/", 1)[1])
            start, _t = self.acts[i]
            return 200, _zip(f"{i}_ACTIVITY.fit", fit_bytes([(0, 49.68, 18.35), (60, 49.681, 18.351)], start=start))
        return 404, b""


@pytest.fixture
def local(tmp_path, monkeypatch):
    monkeypatch.setenv("OB_LOCAL", "1")
    monkeypatch.setattr(club, "ENABLED", False)
    monkeypatch.setattr(garmin_api, "PAUSE_S", 0)
    from webapp import create_app
    app = create_app(str(tmp_path / "instance"))
    app.config["TESTING"] = True
    app.config["OB"].oris_client = FakeOris()
    app.config["OB"].osm = False
    return app


def _now(days_ago, hour=9):
    d = dt.datetime.now(dt.timezone.utc).replace(hour=hour, minute=0, second=0, microsecond=0)
    return d - dt.timedelta(days=days_ago)


def _connect(app, c, fake):
    app.config["OB"].garmin_fetch = fake
    r = c.post("/upload/garmin", data=dict(csrf_token=csrf(c, "/upload"), akce="klic", klic=f"  {KEY}\n"))
    assert r.status_code == 302


def test_not_on_the_server(app, user):
    c = app.test_client()
    assert c.get("/upload/garmin").status_code in (302, 404)
    assert "Garmin Connect</a>" not in c.get("/upload").get_data(as_text=True)


def test_key_only_in_the_data_folder(local):
    c = local.test_client()
    c.get("/")
    html = c.get("/upload/garmin").get_data(as_text=True)
    assert "Personal API" in html and garmin_api.KEY_PAGE in html
    fake = FakeGarmin({})
    _connect(local, c, fake)
    conf = local.config["OB"]
    files = os.listdir(conf.path("garmin"))
    key_file = [f for f in files if f.endswith(".key")][0]
    with open(conf.path("garmin", key_file)) as f:
        assert f.read() == KEY                      # stored without the spaces of the paste
    if os.name == "posix":
        assert os.stat(conf.path("garmin", key_file)).st_mode & 0o077 == 0
    # the key is in no page and in no database row
    assert KEY not in c.get("/upload/garmin").get_data(as_text=True)
    with open(conf.db_path, "rb") as f:
        assert KEY.encode() not in f.read()
    # disconnect deletes it
    c.post("/upload/garmin", data=dict(csrf_token=csrf(c, "/upload"), akce="odpojit"))
    assert os.listdir(conf.path("garmin")) == []


def test_token_cached_and_renewed(local):
    c = local.test_client()
    c.get("/")
    fake = FakeGarmin({1: (_now(3), "running")})
    _connect(local, c, fake)
    c.get("/upload/garmin")
    c.get("/upload/garmin?dni=14")
    assert fake.tokens == 1                         # one token for both lists
    # a token about to expire is replaced
    conf = local.config["OB"]
    tf = [f for f in os.listdir(conf.path("garmin")) if f.endswith(".token.json")][0]
    with open(conf.path("garmin", tf), "w") as f:
        json.dump({"token": _jwt(time.time() + 60), "exp": time.time() + 60}, f)
    c.get("/upload/garmin")
    assert fake.tokens == 2


def test_rejected_key(local):
    c = local.test_client()
    c.get("/")
    fake = FakeGarmin({})
    fake.reject_token = True
    _connect(local, c, fake)
    html = c.get("/upload/garmin").get_data(as_text=True)
    assert "nepřijal" in html and "nový" in html


def test_offer_download_and_pair(local):
    load_handlers()
    c = local.test_client()
    c.get("/")
    fake = FakeGarmin({111: (_now(2), "running"), 112: (_now(5), "orienteering"), 113: (_now(6), "cycling"),
                       114: (_now(300), "running")})
    _connect(local, c, fake)
    html = c.get("/upload/garmin?dni=60").get_data(as_text=True)
    assert 'value="111"' in html and 'value="112"' in html and 'value="113"' in html and 'value="114"' not in html
    checked = set(re.findall(r'value="(\d+)" aria-label="[^"]*"\s*checked', html))
    assert checked == {"111", "112"}                 # a ride is not pre-selected
    r = c.post("/upload/garmin", data=dict(csrf_token=csrf(c, "/upload"), akce="nacist", aktivita=["111", "112"]))
    assert r.status_code in (200, 302)
    run_once(local.config["OB"])
    from webapp import db as dbm
    con = dbm.connect(local.config["OB"].db_path)
    rows = con.execute("SELECT source, original_name FROM activities ORDER BY original_name").fetchall()
    assert [(r["source"], r["original_name"]) for r in rows] == [("garmin-api", "111_ACTIVITY.fit"),
                                                                  ("garmin-api", "112_ACTIVITY.fit")]
    job = con.execute("SELECT status, message FROM jobs WHERE kind = 'garmin_api'").fetchone()
    assert job["status"] == "done" and "Staženo z Garmin Connect 2" in job["message"]
    # now they show as already in the app, and are no longer pre-selected
    html = c.get("/upload/garmin?dni=60").get_data(as_text=True)
    assert html.count(">ano</td>") == 2
    # downloading them again adds nothing
    c.post("/upload/garmin", data=dict(csrf_token=csrf(c, "/upload"), akce="nacist", aktivita=["111"]))
    run_once(local.config["OB"])
    assert con.execute("SELECT COUNT(*) FROM activities").fetchone()[0] == 2


def test_all_runs_as_an_export(local):
    """The hill-model button: every run of the period is handled as a whole export; the runs paired with no
    race and recorded at none are dropped afterwards, as with an export of the account."""
    load_handlers()
    c = local.test_client()
    c.get("/")
    fake = FakeGarmin({121: (_now(2), "running"), 122: (_now(4), "trail_running"), 123: (_now(5), "cycling")})
    _connect(local, c, fake)
    c.post("/upload/garmin", data=dict(csrf_token=csrf(c, "/upload"), akce="vse", dni="60"))
    run_once(local.config["OB"])
    from webapp import db as dbm
    con = dbm.connect(local.config["OB"].db_path)
    job = con.execute("SELECT status, message FROM jobs WHERE kind = 'garmin_api'").fetchone()
    assert job["status"] == "done", job["message"]
    assert "Staženo z Garmin Connect 2" in job["message"] and "V archivu 2 souborů .fit" in job["message"]
    downloads = [p for m, p in fake.calls if p.startswith("/download-service")]
    assert len(downloads) == 2                      # the ride is not downloaded
    assert not os.listdir(local.config["OB"].path("incoming"))   # the zip is gone


def test_page_in_english(local):
    c = local.test_client()
    c.get("/")
    html = c.get("/upload/garmin?lang=en").get_data(as_text=True)
    assert "Personal API key" in html and "Connect Garmin account" in html
    page = html[html.index("Runs from Garmin Connect</h2>"):html.index("<script")]
    assert not re.search("[ěščřžťďňůĚŠČŘŽŤĎŇŮ]", re.sub(r"<[^>]+>", " ", page))
