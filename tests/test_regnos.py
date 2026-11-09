"""More registration numbers after a move to another club (issue 2, docs/oris.md). The fake ORIS answers as the
real one did for runners who moved: one person id for both numbers, getUser only for the number of today, the
entries of that id list the old races under the old number (here BFM0903 of the saved responses)."""
import inspect

import pytest
from conftest import FakeOris, csrf, post, register

from webapp import db as dbm
from webapp import oris
from webapp.services import regnos, sync_oris
from webapp.services import splits as class_splits

# the password the register() helper of conftest gives to a made-up test account
_TEST_PASSWORD = inspect.signature(register).parameters["password"].default


class Moved(FakeOris):
    """Tobiáš moved from BFM to ABC: ORIS gives the person only for ABC0903 now."""
    PEOPLE = dict(FakeOris.PEOPLE, ABC0903=dict(oris_user_id=45118, name="Tobiáš Otta"))

    def user(self, regno):
        return None if regno == "BFM0903" else super().user(regno)


def con_of(app):
    return dbm.connect(app.config["OB"].db_path)


def _timed(con, user_id):
    return con.execute("SELECT COUNT(*) FROM entries WHERE user_id = ? AND official_time_s IS NOT NULL AND splits"
                       " IS NOT NULL", (user_id,)).fetchone()[0]


def test_the_number_of_the_account_is_in_the_list(app, user):
    con = con_of(app)
    assert regnos.of(con, user) == ["BFM0903"]
    assert con.execute("SELECT source FROM user_regnos WHERE user_id = ?", (user,)).fetchone()[0] == "ucet"


def test_old_database_gets_the_list(tmp_path):
    path = str(tmp_path / "app.db")
    con = dbm.connect(path)
    con.executescript("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash TEXT"
                      " NOT NULL, name TEXT, oris_regno TEXT, oris_user_id INTEGER, oris_synced_at TEXT, slope_file"
                      " TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')));"
                      "INSERT INTO users (username, password_hash, oris_regno, oris_user_id)"
                      " VALUES ('tobias', 'x', 'BFM0903', 45118);")
    con.commit()
    dbm.init(path)
    dbm.init(path)   # a second start changes nothing
    assert [tuple(r) for r in con.execute("SELECT regno, oris_user_id, source FROM user_regnos")] == \
        [("BFM0903", 45118, "ucet")]


def test_account_with_the_old_number_still_loads_after_the_move(app, user):
    app.config["OB"].oris_client = Moved()
    con = con_of(app)
    sync_oris.sync_user(con, app.config["OB"], user, pause=0)            # getUser(BFM0903) says nothing now
    assert _timed(con, user) >= 1


def test_account_with_the_new_number_finds_the_old_races(app, client):
    """Two numbers, the same ORIS id: the race under the old number has its official time and split times."""
    app.config["OB"].oris_client = Moved()
    assert register(client, "ABC0903").status_code == 302
    con = con_of(app)
    uid = con.execute("SELECT id FROM users WHERE oris_regno = 'ABC0903'").fetchone()[0]
    sync_oris.sync_user(con, app.config["OB"], uid, pause=0)
    assert regnos.of(con, uid) == ["ABC0903", "BFM0903"]                 # learnt from the entries in ORIS
    assert con.execute("SELECT source FROM user_regnos WHERE regno = 'BFM0903'").fetchone()[0] == "oris"
    assert _timed(con, uid) >= 1
    e = con.execute("SELECT class_id FROM entries WHERE user_id = ? AND official_time_s IS NOT NULL", (uid,)).fetchone()
    t = class_splits.table(con, e["class_id"], regnos.of(con, uid))
    assert t["me"] is not None and t["runners"][t["me"]]["regno"] == "BFM0903"
    # and the old number logs in to the same account
    client.post("/logout", data=dict(csrf_token=csrf(client)))
    r = post(client, "/login", username="BFM0903", password=_TEST_PASSWORD)
    assert r.status_code == 302
    with client.session_transaction() as s:
        assert s["user_id"] == uid


def test_parse_splits_takes_any_number():
    from conftest import oris_fixture
    raw = oris_fixture("getSplits_202420.json")
    assert oris.parse_splits(raw, ["ABC0903", "bfm0903"]) == oris.parse_splits(raw, "BFM0903") is not None
    assert oris.parse_splits(raw, ["ABC0903"]) is None


def test_a_number_of_another_account_is_not_learnt(app, client, user):
    con = con_of(app)
    other = con.execute("INSERT INTO users (username, password_hash, oris_regno) VALUES ('jiny', 'x', 'BFM0002')"
                        ).lastrowid
    con.commit()
    assert not regnos.learn(con, user, "BFM0002", 45118)
    assert regnos.of(con, other) == ["BFM0002"] and regnos.of(con, user) == ["BFM0903"]


# --- the app on one's own computer: adding a number in the profile ------------------------------------------------

@pytest.fixture
def local(tmp_path, monkeypatch):
    monkeypatch.setenv("OB_LOCAL", "1")
    from webapp import club, create_app
    monkeypatch.setattr(club, "ENABLED", False)
    app = create_app(str(tmp_path / "instance"))
    app.config["TESTING"] = True
    app.config["OB"].oris_client = FakeOris()
    c = app.test_client()
    c.post("/profile", data=dict(csrf_token=csrf(c, "/profile"), name="", oris_regno="BFM0903"))
    app.config["OB"].oris_client = Moved()
    return app, c


def _add(c, regno):
    return c.post("/profile/cisla", data=dict(csrf_token=csrf(c, "/profile"), regno=regno), follow_redirects=True)


def test_add_the_new_number_in_the_profile(local):
    app, c = local
    html = _add(c, "abc 0903").get_data(as_text=True)
    assert "Přidáno: ABC0903 (v ORIS Tobiáš Otta)" in html
    con = con_of(app)
    assert regnos.of(con, 1) == ["BFM0903", "ABC0903"]
    assert con.execute("SELECT COUNT(*) FROM jobs WHERE kind = 'sync_oris' AND status = 'queued'").fetchone()[0] == 1
    profile = c.get("/profile").get_data(as_text=True)
    assert "ABC0903" in profile and "BFM0903" in profile and "přidané po přestupu" in profile
    assert "Registrační čísla: BFM0903, ABC0903" in c.get("/").get_data(as_text=True)


def test_a_number_of_someone_else_is_refused(local):
    app, c = local
    assert "patří v ORIS jménu Klára Kolegyně" in _add(c, "BFM0001").get_data(as_text=True)
    con = con_of(app)
    con.execute("INSERT INTO users (username, password_hash, oris_regno) VALUES ('jiny', 'x', 'BFM0002')")
    con.commit()
    assert "patří jinému účtu" in _add(c, "BFM0002").get_data(as_text=True)
    assert "v ORIS není" in _add(c, "XYZ9999").get_data(as_text=True)
    assert regnos.of(con, 1) == ["BFM0903"]


def test_only_a_number_added_by_mistake_can_be_removed(local):
    app, c = local
    _add(c, "ABC0903")
    con = con_of(app)
    gone = lambda regno: c.post(f"/profile/cisla/{regno}/smazat", data=dict(csrf_token=csrf(c, "/profile")),
                                follow_redirects=True).get_data(as_text=True)
    assert "smazat nejde" in gone("BFM0903")                 # the number of the account
    assert "je smazané" in gone("ABC0903")
    assert regnos.of(con, 1) == ["BFM0903"]


def test_no_more_numbers_on_the_server(app, client, user):
    assert client.post("/profile/cisla", data=dict(csrf_token=csrf(client, "/profile"), regno="ABC0903")).status_code \
        == 404
    assert "Přestoupil jsem" not in client.get("/profile").get_data(as_text=True)
