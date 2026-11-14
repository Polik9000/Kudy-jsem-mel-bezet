"""Multi-stage events (issue 11, docs/oris.md): the umbrella event in ORIS is no race here, its stages are.
The fake ORIS answers with small raw dicts shaped like getEvent of 5EOB Tis (an umbrella with Stages/Stage1..,
stages with ParentID and a discipline of their own)."""
import pytest
from conftest import FakeOris, post

from webapp import db as dbm
from webapp import oris
from webapp.services import stages, sync_oris

UMB, E1, E2 = 7000, 7001, 7002
H16_UMB, H16_E1, D16_E1, H16_E2 = 70001, 70011, 70012, 70021


def raw_event(oris_id, name, date, disc, classes, stage_ids=(), parent=None):
    d = dict(ID=str(oris_id), Name=name, Date=date, Place="Tis", LiveloxID="0", GPSLat="49.8", GPSLon="18.1",
             Cancelled="0", Discipline=dict(ShortName=disc[0], NameCZ=disc[1]), Stages=str(len(stage_ids)),
             ParentID=str(parent) if parent else None,
             Classes={f"Class_{cid}": dict(ID=str(cid), Name=cn, Distance="3.1", Climbing="100", Controls="1")
                      for cid, cn in classes})
    for i in range(1, 8):
        d[f"Stage{i}"] = str(stage_ids[i - 1]) if i <= len(stage_ids) else "0"
    return d


EVENTS = {
    UMB: raw_event(UMB, "Tis", "2025-08-03", ("ET", "Etapový závod"), [(H16_UMB, "H16")], stage_ids=(E1, E2)),
    E1: raw_event(E1, "Tis - E1", "2025-08-03", ("MD", "Střední trať"), [(H16_E1, "H16"), (D16_E1, "D16")], parent=UMB),
    E2: raw_event(E2, "Tis - E2", "2025-08-04", ("LD", "Dlouhá trať"), [(H16_E2, "H16")], parent=UMB),
}


def entry(event_id, class_id, date="2025-08-03"):
    return dict(EventID=str(event_id), ClassID=str(class_id), ClassDesc="H16", EventDate=date, RegNo="BFM0903")


class Stages(FakeOris):
    def __init__(self, listed):
        self.listed, self.asked = listed, []

    def entries(self, uid):
        return oris.parse_entries({f"Entry_{i}": e for i, e in enumerate(self.listed)}) if uid == 45118 else []

    def event(self, oris_id):
        self.asked.append(oris_id)
        return oris.parse_event(EVENTS[oris_id])

    def class_splits_raw(self, class_id):
        if class_id == H16_UMB:
            return []
        return dict(Controls={"C1": dict(ControlCode="31"), "C2": dict(ControlCode="")},
                    Splits={"S1": dict(RegNo="BFM0903", ResName="Tobiáš Otta", ResTime="30:00", TotalTime1="10:00",
                                       ResPlace="1.", StartTime="10:00:00")})


def con_of(app):
    return dbm.connect(app.config["OB"].db_path)


def races(con, user):
    return [tuple(r) for r in con.execute(
        "SELECT ev.oris_id, ev.discipline, ev.stage_n, ev.stage_count, e.official_time_s FROM entries e"
        " JOIN classes c ON c.id = e.class_id JOIN events ev ON ev.id = c.event_id WHERE e.user_id = ?"
        " ORDER BY ev.oris_id", (user,))]


TWO_STAGES = [(E1, "Střední trať", 1, 2, 1800), (E2, "Dlouhá trať", 2, 2, 1800)]


def sync(app, user, listed):
    fake = app.config["OB"].oris_client = Stages(listed)
    con = con_of(app)
    sync_oris.sync_user(con, app.config["OB"], user, pause=0)
    return con, fake


def test_parse_event_of_an_umbrella_and_a_stage():
    umb, e1 = oris.parse_event(EVENTS[UMB]), oris.parse_event(EVENTS[E1])
    assert umb["stages"] == [E1, E2] and umb["parent_id"] is None
    assert e1["stages"] == [] and e1["parent_id"] == UMB and e1["discipline"] == "Střední trať"


def test_umbrella_and_stages_listed_give_two_stages_not_three_races(app, user):
    con, fake = sync(app, user, [entry(UMB, H16_UMB), entry(E1, H16_E1), entry(E2, H16_E2, "2025-08-04")])
    assert races(con, user) == TWO_STAGES
    assert not con.execute("SELECT 1 FROM events WHERE oris_id = ?", (UMB,)).fetchone()
    assert sorted(fake.asked) == [UMB, E1, E2]
    fake.asked.clear()
    sync_oris.sync_user(con, app.config["OB"], user, pause=0)
    assert fake.asked == [] and races(con, user) == TWO_STAGES       # the umbrella is remembered, nothing doubled


def test_entry_only_to_the_umbrella_is_spread_over_its_stages(app, user):
    con, _fake = sync(app, user, [entry(UMB, H16_UMB)])
    assert races(con, user) == TWO_STAGES


def test_a_stage_with_its_own_entry_is_not_doubled(app, user):
    con, _fake = sync(app, user, [entry(UMB, H16_UMB), entry(E1, H16_E1)])
    assert races(con, user) == TWO_STAGES


def _old_umbrella(con, user, activity_day=None):
    """The umbrella saved as a race by an older version, with the runner's entry (and a run on that day)."""
    ev = con.execute("INSERT INTO events (oris_id, name, date, discipline) VALUES (?, 'Tis', '2025-08-03', ?)",
                     (UMB, stages.UMBRELLA_DISCIPLINE)).lastrowid
    cls = con.execute("INSERT INTO classes (event_id, name, oris_id) VALUES (?, 'H16', ?)", (ev, H16_UMB)).lastrowid
    act = None
    if activity_day:
        act = con.execute("INSERT INTO activities (user_id, sha1, file, source, start_utc, has_gps) VALUES"
                          " (?, 'abc', 'x.fit', 'fit', ?, 1)", (user, f"{activity_day} 08:00:00")).lastrowid
    con.execute("INSERT INTO entries (user_id, class_id, activity_id, match_confidence) VALUES (?, ?, ?, ?)",
                (user, cls, act, "manual" if act else None))
    con.commit()
    return act


def test_old_umbrella_without_a_run_goes(app, user):
    con = con_of(app)
    _old_umbrella(con, user)
    con, _fake = sync(app, user, [entry(UMB, H16_UMB), entry(E1, H16_E1), entry(E2, H16_E2, "2025-08-04")])
    assert races(con, user) == TWO_STAGES
    assert not con.execute("SELECT 1 FROM events WHERE oris_id = ?", (UMB,)).fetchone()


def test_old_umbrella_with_a_run_hands_it_to_the_stage_of_that_day(app, user):
    con = con_of(app)
    act = _old_umbrella(con, user, "2025-08-04")
    con, _fake = sync(app, user, [entry(UMB, H16_UMB)])
    assert [r[0] for r in races(con, user)] == [E1, E2]
    got = con.execute("SELECT e.activity_id FROM entries e JOIN classes c ON c.id = e.class_id JOIN events ev"
                      " ON ev.id = c.event_id WHERE ev.oris_id = ?", (E2,)).fetchone()[0]
    assert got == act and not con.execute("SELECT 1 FROM events WHERE oris_id = ?", (UMB,)).fetchone()


def test_old_umbrella_entry_moves_to_the_stage_when_the_runner_has_none(app, user):
    con = con_of(app)
    act = _old_umbrella(con, user, "2025-08-04")
    con.execute("INSERT INTO events (oris_id, name, date, discipline, stage_parent) VALUES (?, 'Tis - E2', '2025-08-04',"
                " 'Dlouhá trať', ?)", (E2, UMB))
    con.execute("INSERT INTO classes (event_id, name, oris_id) VALUES ((SELECT id FROM events WHERE oris_id = ?),"
                " 'H16', ?)", (E2, H16_E2))
    con.execute("INSERT INTO oris_umbrellas (oris_id, name, date, stages) VALUES (?, 'Tis', '2025-08-03', ?)",
                (UMB, f"[{E1}, {E2}]"))
    con.commit()
    out = stages.retire(con, UMB)
    assert out == dict(dropped=0, moved=1, kept=False)
    assert races(con, user) == [(E2, "Dlouhá trať", None, None, None)]
    assert con.execute("SELECT activity_id FROM entries").fetchone()[0] == act


def test_old_umbrella_with_a_run_on_no_stage_day_stays(app, user):
    con = con_of(app)
    _old_umbrella(con, user, "2025-09-10")
    con, _fake = sync(app, user, [entry(UMB, H16_UMB)])
    assert UMB in [r[0] for r in races(con, user)]
    assert stages.known(con, UMB)["kept_event_id"] is not None


@pytest.fixture
def stage_oris(app):
    app.config["OB"].oris_client = Stages([])
    return app


def test_add_a_race_from_oris_by_the_umbrella_offers_the_stages(stage_oris, client, user):
    r = post(client, "/races/oris", zavod=str(UMB))
    assert r.status_code == 302 and r.headers["Location"].endswith(f"/races/oris/{UMB}")
    html = client.get(f"/races/oris/{UMB}").get_data(as_text=True)
    assert "Vyber etapu" in html and "E1 / 2" in html and "E2 / 2" in html and "Dlouhá trať" in html
    assert f'/races/oris/{E1}"' in html
    con = con_of(stage_oris)
    assert not con.execute("SELECT 1 FROM events WHERE oris_id = ?", (UMB,)).fetchone()
    assert "H16" in client.get(f"/races/oris/{E1}").get_data(as_text=True)     # then the class of the stage


def test_race_list_shows_discipline_and_stage(app, client, user):
    sync(app, user, [entry(UMB, H16_UMB)])
    html = client.get("/").get_data(as_text=True)
    assert "E1 / 2" in html and "Střední trať" in html and "Etapový závod" not in html
