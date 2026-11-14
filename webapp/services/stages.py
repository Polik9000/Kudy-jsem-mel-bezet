"""Multi-stage events in ORIS (docs/oris.md).

ORIS has an umbrella event (Stages = how many, Stage1..Stage7 = the ORIS ids of the stages, discipline "Etapový
závod") and the stages (ParentID = the umbrella, a discipline of their own: middle, long, sprint). Entries are made
to the umbrella; ORIS then lists the runner in the umbrella and usually in every stage too. Maps, courses and split
times belong to the stages, so only the stages are races here: the umbrella is remembered in oris_umbrellas (one
getEvent) and an entry to it is spread over its stages, in the class of the same name.

An umbrella kept as a race by an older version (retire) goes: an entry without a run is dropped, one with a run
moves to the stage of the day of the run.
"""
import datetime as dt

from oroute import garmin

from ..db import dumps, loads
from . import matching, regnos
from . import splits as class_splits

UMBRELLA_DISCIPLINE = "Etapový závod"   # ORIS discipline ET (NameCZ): how an umbrella from before looks in the database


def known(con, oris_id):
    """The umbrella event with this ORIS id: dict(oris_id, name, date, stages, kept_event_id), or None."""
    row = con.execute("SELECT * FROM oris_umbrellas WHERE oris_id = ?", (oris_id,)).fetchone()
    return dict(row, stages=loads(row["stages"], [])) if row else None


def remember(con, ev):
    """Keep what getEvent said of an umbrella (ev as oris.parse_event gives it) and mark its stages already in
    the database. Returns known()."""
    con.execute("INSERT INTO oris_umbrellas (oris_id, name, date, stages) VALUES (?, ?, ?, ?) ON CONFLICT (oris_id)"
                " DO UPDATE SET name = excluded.name, date = excluded.date, stages = excluded.stages,"
                " fetched_at = datetime('now')", (ev["oris_id"], ev["name"], ev["date"], dumps(ev["stages"])))
    mark(con, ev["oris_id"], ev["stages"])
    return known(con, ev["oris_id"])


def mark(con, umbrella_id, stage_ids):
    """Which stage of how many each stage race in the database is (shown as "E1 / 5")."""
    for n, sid in enumerate(stage_ids, 1):
        con.execute("UPDATE events SET stage_parent = ?, stage_n = ?, stage_count = ? WHERE oris_id = ?",
                    (umbrella_id, n, len(stage_ids), sid))


def suspect(con, event_id):
    """A race from ORIS saved by an older version that may be an umbrella: worth one getEvent."""
    return con.execute("SELECT 1 FROM events WHERE id = ? AND oris_id IS NOT NULL AND discipline = ? AND stage_n IS NULL"
                       " AND oris_id NOT IN (SELECT oris_id FROM oris_umbrellas)",
                       (event_id, UMBRELLA_DISCIPLINE)).fetchone() is not None


def not_umbrella(con, event_id):
    """getEvent said the race is no umbrella: do not ask again."""
    con.execute("UPDATE events SET stage_n = 0 WHERE id = ? AND stage_n IS NULL", (event_id,))


def stages_of(con, umbrella_id):
    """The stage races in the database, in order."""
    return con.execute("SELECT * FROM events WHERE stage_parent = ? ORDER BY stage_n, date", (umbrella_id,)).fetchall()


def _run_day(con, activity_id):
    a = con.execute("SELECT start_utc FROM activities WHERE id = ?", (activity_id,)).fetchone()
    if not a or not a["start_utc"]:
        return None
    return garmin.local(dt.datetime.fromisoformat(a["start_utc"])).date().isoformat()


def _keeps_something(con, e):
    """Has the runner anything in this entry worth keeping: a run, notes, a photo, Livelox screenshots?"""
    one = lambda sql, *args: con.execute(sql, args).fetchone() is not None
    return (e["activity_id"] is not None
            or one("SELECT 1 FROM leg_notes WHERE entry_id = ?", e["id"])
            or one("SELECT 1 FROM photos WHERE entry_id = ?", e["id"])
            or one("SELECT 1 FROM screens WHERE class_id = ? AND user_id = ?", e["class_id"], e["user_id"])
            or one("SELECT 1 FROM pending_screens WHERE class_id = ? AND user_id = ?", e["class_id"], e["user_id"]))


def _times(con, class_id, user_id):
    """The runner's official result in the stored times of a class, as entries columns (or all None)."""
    data = class_splits.load(con, class_id) or {}
    mine = class_splits.my_regno(data.get("runners", []), regnos.of(con, user_id))
    me = next((r for r in data.get("runners", []) if mine and (r.get("regno") or "").upper() == mine), None)
    if me is None:
        return dict(official_time_s=None, start_local=None, result_place=None, splits=None)
    return dict(official_time_s=me["time_s"], start_local=me["start_local"], result_place=me["place"],
                splits=dumps(me["cum"][:-1] + [me["time_s"]]) if me["time_s"] is not None else None)


def _move(con, e, cls):
    """The whole entry goes to the class of the stage (another course: its analysis and leg notes go)."""
    con.execute("UPDATE entries SET class_id = ? WHERE id = ?", (cls["id"], e["id"]))
    t = _times(con, cls["id"], e["user_id"])
    con.execute("UPDATE entries SET official_time_s = ?, start_local = ?, result_place = ?, splits = ? WHERE id = ?",
                (t["official_time_s"], t["start_local"], t["result_place"], t["splits"], e["id"]))
    con.execute("DELETE FROM analyses WHERE entry_id = ?", (e["id"],))
    con.execute("DELETE FROM leg_notes WHERE entry_id = ?", (e["id"],))
    for table in ("screens", "pending_screens"):
        con.execute(f"UPDATE OR IGNORE {table} SET class_id = ? WHERE class_id = ? AND user_id = ?",
                    (cls["id"], e["class_id"], e["user_id"]))
    return e["id"]


def _hand_over(con, e, have):
    """The runner has the stage already (ORIS lists it): the run of the umbrella entry goes to it."""
    con.execute("UPDATE entries SET activity_id = ?, match_confidence = ?, match_note = ?, gps_trim = ? WHERE id = ?",
                (e["activity_id"], e["match_confidence"], e["match_note"], e["gps_trim"], have["id"]))
    if not con.execute("SELECT 1 FROM photos WHERE entry_id = ?", (have["id"],)).fetchone():
        con.execute("UPDATE photos SET entry_id = ? WHERE entry_id = ?", (have["id"], e["id"]))
    con.execute("DELETE FROM entries WHERE id = ?", (e["id"],))
    return have["id"]


def _move_maps(con, ev, stage):
    """The maps uploaded to the umbrella go to the stage where its runner went, where that stage has none."""
    if ev["maponly_file"] and not stage["maponly_file"]:
        con.execute("UPDATE events SET maponly_file = ?, maponly_by = ?, maponly_at = ?, maponly_source = ?,"
                    " maponly_res_m = ?, maponly_acc_m = ? WHERE id = ?",
                    (ev["maponly_file"], ev["maponly_by"], ev["maponly_at"], ev["maponly_source"], ev["maponly_res_m"],
                     ev["maponly_acc_m"], stage["id"]))
        con.execute("UPDATE events SET maponly_file = NULL WHERE id = ?", (ev["id"],))
    for c in con.execute("SELECT * FROM classes WHERE event_id = ? AND course_file IS NOT NULL", (ev["id"],)).fetchall():
        to = con.execute("SELECT id FROM classes WHERE event_id = ? AND name = ? AND course_file IS NULL",
                         (stage["id"], c["name"])).fetchone()
        if to:
            con.execute("UPDATE classes SET course_file = ?, course_by = ?, course_at = ?, course_source = ?,"
                        " course_rms = ?, course_n = ?, course_edge_m = ? WHERE id = ?",
                        (c["course_file"], c["course_by"], c["course_at"], c["course_source"], c["course_rms"],
                         c["course_n"], c["course_edge_m"], to["id"]))
            con.execute("UPDATE classes SET course_file = NULL WHERE id = ?", (c["id"],))


def retire(con, umbrella_id):
    """An umbrella kept as a race by an older version: its entries without anything of the runner go, an entry
    with a run goes to the stage of the day of the run (with the maps of the umbrella); when nothing is left the
    race goes. What cannot be placed stays (oris_umbrellas.kept_event_id). Returns dict(dropped, moved, kept)."""
    out = dict(dropped=0, moved=0, kept=False)
    ev = con.execute("SELECT * FROM events WHERE oris_id = ?", (umbrella_id,)).fetchone()
    if ev is None:
        return out
    by_day = {s["date"]: s for s in stages_of(con, umbrella_id)}
    went = {}
    for e in con.execute("SELECT e.*, c.name AS class_name FROM entries e JOIN classes c ON c.id = e.class_id"
                         " WHERE c.event_id = ?", (ev["id"],)).fetchall():
        if not _keeps_something(con, e):
            con.execute("DELETE FROM entries WHERE id = ?", (e["id"],))
            out["dropped"] += 1
            continue
        stage = by_day.get(_run_day(con, e["activity_id"])) if e["activity_id"] else None
        cls = stage and con.execute("SELECT * FROM classes WHERE event_id = ? AND name = ?",
                                    (stage["id"], e["class_name"])).fetchone()
        if not cls:
            continue
        have = con.execute("SELECT e.* FROM entries e JOIN classes c ON c.id = e.class_id WHERE e.user_id = ?"
                           " AND c.event_id = ?", (e["user_id"], stage["id"])).fetchone()
        notes = con.execute("SELECT 1 FROM leg_notes WHERE entry_id = ?", (e["id"],)).fetchone()
        if have is None:
            entry_id = _move(con, e, cls)
        elif have["activity_id"] is None and not notes:
            entry_id = _hand_over(con, e, have)
        else:
            continue
        went[stage["id"]] = stage
        out["moved"] += 1
        con.commit()
        matching.queue_analysis(con, entry_id)
    if len(went) == 1:
        _move_maps(con, con.execute("SELECT * FROM events WHERE id = ?", (ev["id"],)).fetchone(), next(iter(went.values())))
    left = con.execute("SELECT 1 FROM entries e JOIN classes c ON c.id = e.class_id WHERE c.event_id = ?",
                       (ev["id"],)).fetchone()
    maps = con.execute("SELECT 1 FROM events WHERE id = ? AND maponly_file IS NOT NULL UNION SELECT 1 FROM classes"
                       " WHERE event_id = ? AND course_file IS NOT NULL", (ev["id"], ev["id"])).fetchone()
    if left or maps:
        con.execute("UPDATE oris_umbrellas SET kept_event_id = ? WHERE oris_id = ?", (ev["id"], umbrella_id))
        out["kept"] = True
    else:
        con.execute("DELETE FROM events WHERE id = ?", (ev["id"],))
    con.commit()
    return out
