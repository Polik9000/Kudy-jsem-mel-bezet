"""The daily load from ORIS of every account (flask sync-oris-all): as few requests as ORIS deserves.
ORIS answers from tests/fixtures/oris."""
import datetime as dt

from conftest import FakeOris

from webapp import db as dbm
from webapp.services import sync_oris

NOW = dt.datetime(2026, 10, 6, 12, 0)


class Counting(FakeOris):
    """FakeOris that writes down every request."""

    def __init__(self, down=()):
        self.calls, self.down = [], set(down)

    def _ask(self, what, key=None):
        self.calls.append(what)
        if key in self.down:
            from webapp.oris import OrisError
            raise OrisError(f"ORIS {what}: down")

    def user(self, regno):
        self._ask("getUser", regno)
        return super().user(regno)

    def entries(self, uid):
        self._ask("getUserEventEntries", uid)
        return super().entries(uid)

    def event(self, oris_id):
        self._ask("getEvent")
        return super().event(oris_id)

    def class_splits_raw(self, class_id):
        self._ask("getSplits")
        return super().class_splits_raw(class_id)


def con_of(app):
    return dbm.connect(app.config["OB"].db_path)


def test_sync_all_asks_oris_only_for_what_is_new(app, user):
    con, conf = con_of(app), app.config["OB"]
    con.execute("INSERT INTO users (username, password_hash, oris_regno) VALUES ('klara', 'x', 'BFM0001')")
    con.execute("INSERT INTO users (username, password_hash) VALUES ('bezcisla', 'x')")      # no number: left out
    con.commit()
    ask = Counting()
    r = sync_oris.sync_all(con, conf, client=ask, pause=0, now=NOW, log=lambda s: None)
    assert r == dict(done=2, skipped=0, failed=0)
    # the first time: who klara is, the entries of both, the two races of BFM0903 and their classes
    # (BFM0903 has its ORIS id from the registration)
    assert ask.calls.count("getUser") == 1 and ask.calls.count("getUserEventEntries") == 2
    assert ask.calls.count("getEvent") == 2 and ask.calls.count("getSplits") == 2
    assert con.execute("SELECT COUNT(*) FROM entries WHERE user_id = ?", (user,)).fetchone()[0] == 2
    # an hour later (a cron run twice, a button pressed in the morning): nobody is asked for
    con.execute("UPDATE users SET oris_synced_at = ?", (NOW.isoformat(sep=" "),))
    ask.calls.clear()
    r = sync_oris.sync_all(con, conf, client=ask, pause=0, now=NOW + dt.timedelta(hours=1), log=lambda s: None)
    assert r == dict(done=0, skipped=2, failed=0) and ask.calls == []
    # the next day: only the entries (the ORIS ids are known, both races are old and stored)
    r = sync_oris.sync_all(con, conf, client=ask, pause=0, now=NOW + dt.timedelta(hours=25), log=lambda s: None)
    assert r["done"] == 2 and ask.calls == ["getUserEventEntries", "getUserEventEntries"]


def test_one_account_failing_does_not_stop_the_others(app, user):
    con, conf = con_of(app), app.config["OB"]
    con.execute("INSERT INTO users (username, password_hash, oris_regno, oris_user_id)"
                " VALUES ('klara', 'x', 'BFM0001', 90001)")
    con.execute("UPDATE users SET oris_user_id = 45118 WHERE id = ?", (user,))
    con.commit()
    said = []
    ask = Counting(down={90001})
    r = sync_oris.sync_all(con, conf, client=ask, pause=0, now=NOW, log=said.append)
    assert r == dict(done=1, skipped=0, failed=1)
    assert any(s.startswith("BFM0001: ORIS getUserEventEntries: down") for s in said), said
    assert any(s.startswith("BFM0903: ORIS: 2 závodů (2 nových)") for s in said), said


def test_sync_oris_all_command(app, user):
    con = con_of(app)
    con.execute("UPDATE users SET oris_synced_at = datetime('now') WHERE id = ?", (user,))
    con.commit()
    out = app.test_cli_runner().invoke(args=["sync-oris-all"])
    assert out.exit_code == 0 and "0 accounts loaded, 1 loaded recently, 0 failed" in out.output, out.output
    out = app.test_cli_runner().invoke(args=["sync-oris-all", "--hours", "0"])
    assert out.exit_code == 0 and "1 accounts loaded" in out.output, out.output



def test_upsert_class_survives_same_name_in_one_race(app):
    """ORIS can list two classes of a race under one name, and a class may already exist without its ORIS id:
    neither stops the load (UNIQUE constraint failed: classes.event_id, classes.name)."""
    con = con_of(app)
    ev = con.execute("INSERT INTO events (name, date, oris_id) VALUES ('Zavod', '2026-10-01', 777)").lastrowid
    hand = con.execute("INSERT INTO classes (event_id, name) VALUES (?, 'D21')", (ev,)).lastrowid
    c = dict(oris_id=5001, name="D21", distance_km=5.0, climb_m=100, controls=15)
    assert sync_oris.upsert_class(con, ev, c) == hand                      # adopted, not duplicated
    assert con.execute("SELECT oris_id FROM classes WHERE id = ?", (hand,)).fetchone()[0] == 5001
    twin = sync_oris.upsert_class(con, ev, dict(c, oris_id=5002))          # same name, other ORIS class
    assert twin != hand
    assert con.execute("SELECT name FROM classes WHERE id = ?", (twin,)).fetchone()[0] == "D21 (5002)"
    assert sync_oris.upsert_class(con, ev, dict(c, oris_id=5002)) == twin  # and a second load changes nothing
    assert con.execute("SELECT COUNT(*) FROM classes WHERE event_id = ?", (ev,)).fetchone()[0] == 2
