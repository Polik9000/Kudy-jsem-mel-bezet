"""One account per registration number, and removing an account with everything that is only its own."""
import datetime as dt
import io
import os
import sqlite3

import pytest
from conftest import FakeOris, clear_jobs, csrf, post, register
from races import inputs

from webapp import db as dbm
from webapp.services import accounts, sync_oris
from webapp.worker import load_handlers, run_once


def con_of(app):
    return dbm.connect(app.config["OB"].db_path)


def test_one_account_per_registration_number(app, client, user):
    con = con_of(app)
    # the database itself refuses a second account with the number ...
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("INSERT INTO users (username, password_hash, oris_regno) VALUES ('jiny', 'x', 'BFM0903')")
    con.rollback()
    # ... accounts without a number are not limited ...
    con.execute("INSERT INTO users (username, password_hash) VALUES ('bez1', 'x')")
    con.execute("INSERT INTO users (username, password_hash) VALUES ('bez2', 'x')")
    con.commit()
    # ... the registration form says so ...
    post(client, "/logout")
    html = register(client, "BFM0903", "jineheslo123").get_data(as_text=True)
    assert "už existuje" in html
    assert con.execute("SELECT COUNT(*) FROM users WHERE oris_regno = 'BFM0903'").fetchone()[0] == 1
    # ... and another account cannot take the number in its profile
    assert register(client, "BFM0001").status_code == 302
    post(client, "/profile", oris_regno="bfm0903", name="")
    assert con.execute("SELECT oris_regno FROM users WHERE username = 'BFM0001'").fetchone()[0] == "BFM0001"


def test_registration_number_of_an_account_is_fixed_in_the_database(app, client, user):
    con = con_of(app)
    for new in ("BFM0001", None):
        with pytest.raises(sqlite3.IntegrityError, match="cannot be changed"):
            con.execute("UPDATE users SET oris_regno = ? WHERE id = ?", (new, user))
        con.rollback()
    con.execute("UPDATE users SET oris_regno = 'BFM0903', name = 'Jiné jméno' WHERE id = ?", (user,))  # the same: fine
    # an account from before the numbers (login name only) may still get one
    old = con.execute("INSERT INTO users (username, password_hash) VALUES ('stary', 'x')").lastrowid
    con.execute("UPDATE users SET oris_regno = 'BFM0002' WHERE id = ?", (old,))
    con.commit()


def test_old_database_gets_the_rule_too(tmp_path):
    path = str(tmp_path / "app.db")
    con = dbm.connect(path)
    con.executescript("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash TEXT"
                      " NOT NULL, name TEXT, oris_regno TEXT, oris_user_id INTEGER, oris_synced_at TEXT, slope_file"
                      " TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')));"
                      "INSERT INTO users (username, password_hash, oris_regno) VALUES ('tobias', 'x', 'BFM0903');")
    con.commit()
    dbm.init(path)
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("UPDATE users SET oris_regno = 'BFM0305'")


def test_invite_command(app, client, user, monkeypatch):
    monkeypatch.setenv("OB_INSTANCE", app.config["OB"].instance)
    run = app.test_cli_runner()
    r = run.invoke(args=["invite", "bfm 0001", "BFM0903", "--site", "https://klub.example/"])
    assert r.exit_code == 0, r.output
    new, taken = r.output.splitlines()
    regno, code, link = new.split()
    assert regno == "BFM0001" and link == f"https://klub.example/ob/register?regno=BFM0001&kod={code}"
    assert taken.startswith("BFM0903 ") and taken.endswith("(already has an account)")
    # the printed code is the one the registration form takes
    post(client, "/logout")
    assert register(client, "BFM0001", code=code).status_code == 302
    assert run.invoke(args=["invite", "bob"]).exit_code != 0


def test_old_database_with_shared_numbers_still_starts(tmp_path, capsys):
    path = str(tmp_path / "app.db")
    con = dbm.connect(path)
    con.executescript("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash TEXT"
                      " NOT NULL, name TEXT, oris_regno TEXT, oris_user_id INTEGER, oris_synced_at TEXT, slope_file"
                      " TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')));"
                      "INSERT INTO users (username, password_hash, oris_regno) VALUES ('tobias', 'x', 'BFM0903');"
                      "INSERT INTO users (username, password_hash, oris_regno) VALUES ('tobiasotta', 'x', 'BFM0903');")
    con.commit()
    dbm.init(path)                                        # does not fail, says what to do
    assert "BFM0903" in capsys.readouterr().out
    index = lambda: con.execute("SELECT 1 FROM sqlite_master WHERE name = 'users_regno'").fetchone()
    assert index() is None
    con.execute("DELETE FROM users WHERE username = 'tobias'")
    con.commit()
    dbm.init(path)
    assert index() is not None


def scene(app, client, user):
    """A runner with an ORIS race (activity, shared maps, a forbidden line) and a race added by hand with its
    own map; a clubmate at the same ORIS race."""
    conf, con = app.config["OB"], con_of(app)
    sync_oris.sync_user(con, conf, user, client=FakeOris(), today=dt.date(2026, 10, 6), pause=0)
    mine = con.execute("SELECT e.id, c.event_id FROM entries e JOIN classes c ON c.id = e.class_id JOIN events ev"
                       " ON ev.id = c.event_id WHERE ev.oris_id = 8989").fetchone()
    course, maponly, fit = inputs("pohora")

    def upload(page, kind, path):
        with open(path, "rb") as f:
            data = dict(csrf_token=csrf(client), kind=kind, kmz=(io.BytesIO(f.read()), "m.kmz"))
        r = client.post(page + "/map", data=data, content_type="multipart/form-data")
        assert r.status_code == 302
    with open(fit, "rb") as f:
        client.post("/upload", data=dict(csrf_token=csrf(client), files=(io.BytesIO(f.read()), "run.fit")),
                    content_type="multipart/form-data")
    load_handlers()
    run_once(conf)
    upload(f"/races/{mine['id']}", "maponly", maponly)
    r = post(client, "/races/new", name="Azymut Cup", date="2026-08-14", class_name="O3", time="76:57")
    upload(r.headers["Location"], "maponly", inputs("azymut-e5")[1])
    client.post(f"/races/{mine['id']}/barriers", json=dict(line=[[49.56, 16.76], [49.561, 16.761]]),
                headers={"X-CSRF-Token": csrf(client)})
    clear_jobs(app)
    post(client, "/logout")
    register(client, "BFM0001")
    clear_jobs(app)
    mate = con.execute("SELECT id FROM users WHERE username = 'BFM0001'").fetchone()["id"]
    # the other class of the race, kept by the sync with the one entered
    cls = con.execute("SELECT id FROM classes WHERE event_id = ? AND name = 'D21C'", (mine["event_id"],)).fetchone()[0]
    con.execute("INSERT INTO entries (user_id, class_id) VALUES (?, ?)", (mate, cls))
    con.commit()
    return con, conf, mine["event_id"], mate


def test_delete_account_takes_what_is_its_own_and_leaves_what_is_shared(app, client, user):
    con, conf, event, mate = scene(app, client, user)
    count = lambda sql, *a: con.execute(sql, a).fetchone()[0]
    manual = con.execute("SELECT id FROM events WHERE oris_id IS NULL").fetchone()["id"]
    assert os.path.isdir(conf.path("fit", f"user_{user}")) and os.path.isdir(conf.path("maps", f"event_{manual}"))
    assert accounts.summary(con, user)["races"] == 3 and accounts.summary(con, user)["activities"] == 1

    had = accounts.delete_user(con, conf, user)
    assert had["races"] == 3
    assert count("SELECT COUNT(*) FROM users WHERE id = ?", user) == 0
    assert count("SELECT COUNT(*) FROM entries WHERE user_id = ?", user) == 0
    assert count("SELECT COUNT(*) FROM activities") == 0 and not os.path.exists(conf.path("fit", f"user_{user}"))
    # the race added by hand was only this runner's: gone with its map
    assert count("SELECT COUNT(*) FROM events WHERE oris_id IS NULL") == 0
    assert not os.path.exists(conf.path("maps", f"event_{manual}"))
    # the ORIS race is shared: the event, its map and the forbidden line stay, only "who" is forgotten
    ev = con.execute("SELECT * FROM events WHERE id = ?", (event,)).fetchone()
    assert ev["maponly_file"] and ev["maponly_by"] is None and os.path.exists(conf.path(ev["maponly_file"]))
    assert count("SELECT COUNT(*) FROM barriers WHERE event_id = ? AND created_by IS NULL", event) == 1
    assert count("SELECT COUNT(*) FROM class_splits") == 2
    # the clubmate is untouched and still sees the shared map
    assert count("SELECT COUNT(*) FROM entries WHERE user_id = ?", mate) == 1
    # the number is free again: the account can be made anew
    post(client, "/logout")
    assert register(client, "BFM0903", "noveheslo123").status_code == 302
    assert count("SELECT COUNT(*) FROM users WHERE oris_regno = 'BFM0903'") == 1


def test_runner_closes_their_own_account_from_the_profile(app, client, user):
    con, conf, event, mate = scene(app, client, user)
    count = lambda sql, *a: con.execute(sql, a).fetchone()[0]
    post(client, "/logout")                                                 # scene() ends logged in as the clubmate
    assert post(client, "/login", username="BFM0903", password="tajneheslo").status_code == 302
    html = client.get("/profile").get_data(as_text=True)
    flat = " ".join(html.split())          # the page wraps its lines where the template does
    assert "Zrušení účtu" in html and "závody v aplikaci (3)" in flat and "běhy z hodinek (1)" in flat
    # the password confirms it
    r = client.post("/account/delete", data=dict(csrf_token=csrf(client), password="spatneheslo"), follow_redirects=True)
    assert "Heslo nesedí, účet zůstává." in r.get_data(as_text=True) and count("SELECT COUNT(*) FROM users") == 2
    manual = con.execute("SELECT id FROM events WHERE oris_id IS NULL").fetchone()["id"]
    r = client.post("/account/delete", data=dict(csrf_token=csrf(client), password="tajneheslo"), follow_redirects=True)
    assert "Účet je zrušený" in r.get_data(as_text=True) and "Přihlášení" in r.get_data(as_text=True)
    # the same as the command: rows and files of the runner are gone, what a race shares stays
    assert [u["username"] for u in con.execute("SELECT username FROM users")] == ["BFM0001"]
    assert count("SELECT COUNT(*) FROM entries WHERE user_id = ?", user) == 0
    assert count("SELECT COUNT(*) FROM activities") == 0
    assert not os.path.exists(conf.path("fit", f"user_{user}")) and not os.path.exists(conf.path("maps", f"event_{manual}"))
    ev = con.execute("SELECT * FROM events WHERE id = ?", (event,)).fetchone()
    assert ev["maponly_file"] and ev["maponly_by"] is None and os.path.exists(conf.path(ev["maponly_file"]))
    assert count("SELECT COUNT(*) FROM barriers WHERE event_id = ? AND created_by IS NULL", event) == 1
    assert count("SELECT COUNT(*) FROM entries WHERE user_id = ?", mate) == 1
    # logged out, and the old password opens nothing
    assert client.get("/profile").status_code == 302
    assert post(client, "/login", username="BFM0903", password="tajneheslo").status_code == 200


def test_delete_account_command(app, client, user, monkeypatch):
    con, conf, event, mate = scene(app, client, user)
    monkeypatch.setenv("OB_INSTANCE", conf.instance)
    run = app.test_cli_runner()
    r = run.invoke(args=["delete-account", "bfm0903"])
    assert "BFM0903" in r.output and "3 races" in r.output and "nothing deleted" in r.output
    assert con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 2
    r = run.invoke(args=["delete-account", "bfm0903", "--yes"])
    assert "deleted" in r.output and r.exit_code == 0
    assert [u["username"] for u in con.execute("SELECT username FROM users")] == ["BFM0001"]
    assert run.invoke(args=["delete-account", "nobody", "--yes"]).exit_code != 0


def test_seed_demo_goes_to_the_account_that_has_the_number(app, client, user, monkeypatch):
    conf, con = app.config["OB"], con_of(app)
    monkeypatch.setenv("OB_INSTANCE", conf.instance)
    run = app.test_cli_runner()
    # the demo races belong to BFM0903: another name cannot take them while that account exists
    r = run.invoke(args=["seed-demo", "nekdo", "--password", "dlouheheslo1"])
    assert r.exit_code != 0 and "BFM0903" in r.output
    assert con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    r = run.invoke(args=["seed-demo", "BFM0903"])
    assert r.exit_code == 0, r.output
    assert con.execute("SELECT COUNT(*) FROM entries WHERE user_id = ?", (user,)).fetchone()[0] == 4
    assert con.execute("SELECT COUNT(*) FROM entries WHERE activity_id IS NOT NULL").fetchone()[0] == 4
    assert con.execute("SELECT COUNT(*) FROM jobs WHERE kind = 'analyse' AND status = 'queued'").fetchone()[0] == 4
