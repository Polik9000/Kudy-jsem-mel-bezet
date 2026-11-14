"""A disqualified run (a missed control, DISK in ORIS): its punches and the finish on the clock are kept as the
entry's split times, so Livelox screenshots and photos of the race are placed (they waited for "splits from ORIS"
for ever before), and the message after an upload says what is really missing."""
import io

from conftest import csrf
from test_web_photo import entry, jpeg_bytes

from webapp import oris
from webapp.db import dumps, loads
from webapp.services import matching
from webapp.services import splits as class_splits


def _raw(res_time="DISK", t2=""):
    """A getSplits answer of a small class: the runner BFM0903 missed the second control."""
    return dict(Controls={"Control_1": dict(ControlCode="31"), "Control_2": dict(ControlCode="32"),
                          "Control_3": dict(ControlCode="100"), "Control_4": dict(ControlCode="")},
                Splits={"Split_1": dict(RegNo="BFM0903", ResName="Otta Tobiáš", ResTime=res_time, ResPlace="",
                                        StartTime="11:04:00", FinishTime="11:55:38",
                                        TotalTime1="1:13", TotalTime2=t2, TotalTime3="50:59")})


def test_disqualified_runner_keeps_punches_and_the_finish_on_the_clock():
    s = oris.parse_splits(_raw(), "bfm0903")
    assert s["control_codes"] == ["31", "32", "100"]
    assert s["time_s"] is None and s["status"] == "DISK"
    assert s["cumulative"] == [73, None, 3059, 3098]
    assert oris.usable_splits(s) == [73, None, 3059, 3098]
    # nothing on the clock and no punch: nothing to place the map by
    assert oris.usable_splits(dict(time_s=None, cumulative=[None, None, None])) is None
    # classified: kept as it always was
    ok = oris.parse_splits(_raw("51:38", "2:33"), "BFM0903")
    assert ok["time_s"] == 3098 and ok["status"] == "OK" and oris.usable_splits(ok) == [73, 153, 3059, 3098]


def _disqualify(con, entry_id, user_id, in_results=True):
    """The entry as an older version left a DISK run: a run from the watch, no splits of its own; the class splits
    hold the runner with a missed control (or not at all)."""
    cls = con.execute("SELECT class_id FROM entries WHERE id = ?", (entry_id,)).fetchone()["class_id"]
    aid = con.execute("INSERT INTO activities (user_id, sha1, file, source, start_utc, has_gps)"
                      " VALUES (?, 'x', 'fit/x.fit', 'fit', '2025-05-17T09:00:00+00:00', 1)", (user_id,)).lastrowid
    con.execute("UPDATE entries SET activity_id = ?, match_confidence = 'manual', splits = NULL,"
                " official_time_s = NULL WHERE id = ?", (aid, entry_id))
    runners = [dict(name="Otta Tobiáš", regno="BFM0903", club=None, place=None, start_local="11:04:00",
                    time_s=None, status="DISK", cum=[73, None, 3059, 3098])] if in_results else \
              [dict(name="Někdo Jiný", regno="BFM0806", club=None, place="1", start_local="11:08:00",
                    time_s=3369, status="OK", cum=[330, 409, 3318, 3369])]
    con.execute("INSERT INTO class_splits (class_id, data) VALUES (?, ?) ON CONFLICT (class_id) DO UPDATE SET"
                " data = excluded.data", (cls, dumps(dict(control_codes=["31", "32", "100"], runners=runners))))
    con.commit()
    return cls


def test_screenshots_of_a_disqualified_run_are_queued(app, client, user):
    con, mine = entry(app, client, user, run=False)
    cls = _disqualify(con, mine, user)
    con.execute("INSERT INTO pending_screens (class_id, user_id, course_file) VALUES (?, ?, 'screens/a.png')",
                (cls, user))
    con.commit()
    queued = matching.queue_waiting_screens(con, user)
    assert len(queued) == 1
    assert loads(con.execute("SELECT splits FROM entries WHERE id = ?", (mine,)).fetchone()["splits"]) == \
        [73, None, 3059, 3098]
    assert con.execute("SELECT queued FROM pending_screens WHERE class_id = ?", (cls,)).fetchone()["queued"] == 1


def test_not_in_the_results_of_the_class_says_so(app, client, user):
    con, mine = entry(app, client, user, run=False)
    _disqualify(con, mine, user, in_results=False)
    assert class_splits.fill_missing(con, user) == []
    html = client.post(f"/races/{mine}/files", data=dict(csrf_token=csrf(client),
                                                       screen_course=(io.BytesIO(jpeg_bytes()), "trat.jpg")),
                       content_type="multipart/form-data", follow_redirects=True).get_data(as_text=True)
    assert "zatím se neusadí" in html and "tě nevidím" in html and "Jakmile bude k dispozici" not in html
