"""Runs from a watch connected by USB, or from a folder (TODO 55, services/watch.py)."""
import os
import re

import pytest
from conftest import FakeOris, csrf
from fitfile import fit_bytes

from webapp import club
from webapp import db as dbm
from webapp.services import watch


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


def run(shift):
    return fit_bytes([(t, 50.0 + shift + t * 1e-5, 18.0) for t in range(0, 600, 2)])


@pytest.fixture
def card(tmp_path):
    """A watch disk: GARMIN/Activity with three runs, one file that is no activity, and a note."""
    d = tmp_path / "disk" / "GARMIN" / "Activity"
    d.mkdir(parents=True)
    for i, name in enumerate(("2026-01-01-10-00-00.fit", "2026-01-02-10-00-00.fit", "2026-01-03-10-00-00.fit")):
        (d / name).write_bytes(run(i * 0.01))
    (d / "broken.fit").write_bytes(b"not a fit file at all, only some text of the same kind of length")
    (d / "notes.txt").write_text("x")
    return tmp_path / "disk"


def test_three_runs_two_new_after_one_is_there(local, card):
    from webapp import db as d
    c = local.test_client()
    c.get("/")
    con = d.connect(local.config["OB"].db_path)
    uid = con.execute("SELECT id FROM users").fetchone()["id"]
    base, rows = watch.offer(con, uid, str(card))              # the disk: its Activity folder is found
    assert base.endswith(os.path.join("GARMIN", "Activity")) and len(rows) == 3 and all(r["new"] for r in rows)
    # one of the three is loaded already
    c.post("/upload/hodinky", data=dict(csrf_token=csrf(c, "/"), slozka=str(card), soubor=rows[0]["name"]))
    assert con.execute("SELECT COUNT(*) FROM activities").fetchone()[0] == 1
    base, rows = watch.offer(con, uid, str(card))
    assert sorted(r["new"] for r in rows) == [False, True, True]
    # the page offers the two, ticked, and says which one is there already
    html = c.get("/upload/hodinky", query_string=dict(slozka=str(card))).get_data(as_text=True)
    assert html.count('name="soubor"') == 2 and "už v aplikaci" in html and "nových 2" in html
    names = [r["name"] for r in rows if r["new"]]
    r = c.post("/upload/hodinky", data=dict(csrf_token=csrf(c, "/"), slozka=str(card), soubor=names))
    assert r.status_code == 302
    assert con.execute("SELECT COUNT(*) FROM activities").fetchone()[0] == 3
    assert "Načteno běhů: 2" in c.get("/upload").get_data(as_text=True)
    # nothing new left
    assert not any(r["new"] for r in watch.offer(con, uid, str(card))[1])
    assert re.search(r"nových 0", c.get("/upload/hodinky", query_string=dict(slozka=str(card))).get_data(as_text=True))


def test_only_names_the_folder_offered_are_loaded(local, card, tmp_path):
    c = local.test_client()
    c.get("/")
    secret = tmp_path / "secret.fit"
    secret.write_bytes(run(0.5))
    c.post("/upload/hodinky", data=dict(csrf_token=csrf(c, "/"), slozka=str(card),
                                        soubor=["../../../secret.fit", "broken.fit", "notes.txt"]))
    con = dbm.connect(local.config["OB"].db_path)
    assert con.execute("SELECT COUNT(*) FROM activities").fetchone()[0] == 0


def test_missing_folder(local, tmp_path):
    c = local.test_client()
    assert "neexistuje" in c.get("/upload/hodinky", query_string=dict(slozka=str(tmp_path / "none")),
                                 follow_redirects=True).get_data(as_text=True)


def test_not_on_the_server(app, client, user):
    assert client.get("/upload/hodinky").status_code == 404


def test_watch_disks_are_found_by_their_folder(monkeypatch, tmp_path):
    (tmp_path / "GARMIN" / "Activity").mkdir(parents=True)
    monkeypatch.setattr(watch.sys, "platform", "darwin")
    monkeypatch.setattr(watch.glob, "glob", lambda pattern: [str(tmp_path), str(tmp_path / "other")])
    assert watch.watch_folders() == [str(tmp_path / "GARMIN" / "Activity")]
