"""Backups of the database and of the uploaded files that cannot be got again (flask backup, flask restore),
and the daily jobs of a club server (webapp/cron.py)."""
import datetime as dt
import hashlib
import os
import sqlite3

from webapp import cron
from webapp import db as dbm
from webapp.services import backup


def con_of(app):
    return dbm.connect(app.config["OB"].db_path)


def scene(app, user):
    """An account with what cannot be got again: a .fit, a map without course, a photo, an own slope."""
    conf = app.config["OB"]
    con = con_of(app)
    files = {"fit/user_1/abc.fit": b"FIT" * 100, "maps/event_1/maponly.kmz": b"KMZ" * 1000,
             "photos/entry_1.jpg": b"JPG" * 50, "models/user_1/slope.json": b'{"curve": []}',
             "analyses/entry_1/best/best.json": b"{}"}                       # computed: not in the backup
    for rel, data in files.items():
        os.makedirs(os.path.dirname(conf.path(rel)), exist_ok=True)
        with open(conf.path(rel), "wb") as f:
            f.write(data)
    con.execute("INSERT INTO events (name, date, maponly_file) VALUES ('Pohora', '2025-05-17', 'maps/event_1/maponly.kmz')")
    con.execute("INSERT INTO classes (event_id, name) VALUES (1, 'H16C')")
    con.execute("INSERT INTO activities (user_id, sha1, file, source, start_utc, has_gps) VALUES"
                " (?, 'abc', 'fit/user_1/abc.fit', 'upload', '2025-05-17T08:00:00+00:00', 1)", (user,))
    con.execute("INSERT INTO entries (user_id, class_id, activity_id) VALUES (?, 1, 1)", (user,))
    con.execute("INSERT INTO photos (entry_id, file) VALUES (1, 'photos/entry_1.jpg')")
    con.execute("UPDATE users SET slope_file = 'models/user_1/slope.json' WHERE id = ?", (user,))
    con.commit()
    return files


def test_backup_and_restore(app, user, tmp_path):
    conf = app.config["OB"]
    files = scene(app, user)
    dest = tmp_path / "zalohy"
    r = backup.backup(conf, str(dest), now=dt.datetime(2026, 10, 20, 4, 30))
    assert os.path.basename(r["db"]) == "ob-2026-10-20_0430.db" and r["files"] == 4 and r["copied"] == 4
    listed = open(r["list"], encoding="utf-8").read()
    assert "fit/user_1/abc.fit\t300\t" + hashlib.sha1(files["fit/user_1/abc.fit"]).hexdigest() in listed
    assert "mapa bez tratě" in listed and "fotka mapy" in listed and "vlastní sklon" in listed
    assert "best.json" not in listed
    with sqlite3.connect(r["db"]) as c:
        assert c.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    # the next day nothing has changed: nothing is copied again
    assert backup.backup(conf, str(dest), now=dt.datetime(2026, 10, 21, 4, 30))["copied"] == 0

    # the server is lost: a new, empty instance gets the backup back
    from webapp import create_app
    new = create_app(str(tmp_path / "nova"))
    out = new.test_cli_runner().invoke(args=["restore", r["db"]])
    assert "run again with --yes" in out.output and not os.path.exists(new.config["OB"].path("fit"))
    out = new.test_cli_runner().invoke(args=["restore", r["db"], "--yes"])
    assert out.exit_code == 0 and "4 of 4 files put back" in out.output, out.output
    nconf = new.config["OB"]
    for rel, data in files.items():
        if not rel.startswith("analyses/"):
            assert open(nconf.path(rel), "rb").read() == data
    con = dbm.connect(nconf.db_path)
    assert con.execute("SELECT username FROM users WHERE id = ?", (user,)).fetchone()[0] == "BFM0903"
    assert con.execute("SELECT maponly_file FROM events").fetchone()[0] == "maps/event_1/maponly.kmz"
    # ... and the app runs on it: the runner logs in and sees the race
    c = new.test_client()
    from conftest import post
    assert post(c, "/login", username="BFM0903", password="tajneheslo").status_code == 302
    assert "Pohora" in c.get("/").get_data(as_text=True)


def test_only_the_last_backups_are_kept_and_the_mirror_follows_them(app, user, tmp_path):
    conf = app.config["OB"]
    scene(app, user)
    dest = str(tmp_path / "zalohy")
    for day in range(1, 5):
        backup.backup(conf, dest, keep=2, now=dt.datetime(2026, 10, day, 4, 30))
    assert sorted(os.listdir(dest)) == ["ob-2026-10-03_0430-soubory.txt", "ob-2026-10-03_0430.db",
                                        "ob-2026-10-04_0430-soubory.txt", "ob-2026-10-04_0430.db", "soubory"]
    # the photo is gone from the app: two backups later it is gone from the mirror too
    con = con_of(app)
    con.execute("DELETE FROM photos")
    con.commit()
    os.remove(conf.path("photos/entry_1.jpg"))
    backup.backup(conf, dest, keep=2, now=dt.datetime(2026, 10, 5, 4, 30))
    assert os.path.exists(os.path.join(dest, "soubory", "photos", "entry_1.jpg"))      # the 4th still lists it
    r = backup.backup(conf, dest, keep=2, now=dt.datetime(2026, 10, 6, 4, 30))
    assert r["removed"] == 1 and not os.path.exists(os.path.join(dest, "soubory", "photos", "entry_1.jpg"))


def test_backup_command(app, user, tmp_path, monkeypatch):
    monkeypatch.setenv("OB_BACKUP_DIR", str(tmp_path / "b"))
    out = app.test_cli_runner().invoke(args=["backup"])
    assert out.exit_code == 0 and "database: " in out.output and str(tmp_path / "b") in out.output, out.output


def test_cron_runs_what_is_switched_on(app, user, monkeypatch, tmp_path):
    assert cron.next_run(dt.datetime(2026, 10, 20, 3, 0), "04:30") == dt.datetime(2026, 10, 20, 4, 30)
    assert cron.next_run(dt.datetime(2026, 10, 20, 5, 0), "04:30") == dt.datetime(2026, 10, 21, 4, 30)
    monkeypatch.setenv("OB_BACKUP_DIR", str(tmp_path / "b"))
    monkeypatch.setenv("OB_CRON_ORIS", "0")
    said = []
    cron.run_jobs(app.config["OB"], said.append)
    assert len(said) == 1 and said[0].startswith("backup: ") and os.listdir(tmp_path / "b")
    monkeypatch.setenv("OB_CRON_BACKUP", "0")
    monkeypatch.setenv("OB_CRON_ORIS", "1")
    said.clear()
    cron.run_jobs(app.config["OB"], said.append)        # (FakeOris of the app)
    assert said[-1] == "ORIS: 1 accounts loaded, 0 loaded recently, 0 failed", said

