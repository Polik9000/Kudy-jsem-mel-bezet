"""Pair the runner's activities with their races (rule: oroute.garmin.match_race) and queue the analysis."""
import datetime as dt

from oroute import garmin

from ..db import loads
from . import jobs


def _activities(con, user_id):
    return [dict(id=r["id"], start=dt.datetime.fromisoformat(r["start_utc"]), sport=r["sport"],
                 sub_sport=r["sub_sport"], timer=r["timer_s"], has_gps=bool(r["has_gps"]), lat=r["lat"], lon=r["lon"])
            for r in con.execute("SELECT * FROM activities WHERE user_id = ? AND start_utc IS NOT NULL", (user_id,))]


def places(ev):
    """[(lat, lon)] of a race: the ORIS centre and its named places (events.lat/lon, events.locations)."""
    out = [(ev["lat"], ev["lon"])] if ev["lat"] is not None and ev["lon"] is not None and (ev["lat"] or ev["lon"]) else []
    return out + [(l["lat"], l["lon"]) for l in loads(ev["locations"], [])]


def match_user(con, user_id, queue=True):
    """Match every race of the user that was not paired by hand. Returns the entries whose activity changed
    (and, unless queue is False, queues their analysis)."""
    acts = _activities(con, user_id)
    changed = []
    rows = con.execute(
        "SELECT e.*, ev.date, ev.lat, ev.lon, ev.locations FROM entries e JOIN classes c ON c.id = e.class_id"
        " JOIN events ev ON ev.id = c.event_id"
        " WHERE e.user_id = ? AND e.match_confidence IS NOT 'manual'", (user_id,)).fetchall()
    for e in rows:
        best, conf, note = garmin.match_race(dt.date.fromisoformat(e["date"]), e["official_time_s"], acts,
                                             e["start_local"], near=places(e))
        aid = best["id"] if best else None
        if aid != e["activity_id"] or conf != e["match_confidence"] or note != e["match_note"]:
            con.execute("UPDATE entries SET activity_id = ?, match_confidence = ?, match_note = ? WHERE id = ?",
                        (aid, conf, note, e["id"]))
            if aid != e["activity_id"]:
                changed.append(e["id"])
    con.commit()
    for entry_id in changed if queue else []:
        queue_analysis(con, entry_id)
    return changed


KEEP_KM = 15.0   # a run that starts this close to a race on the day of the race is kept, paired or not


def at_races(con, user_id):
    """The runner's activities that are paired with no race but were recorded on the day of one of their races
    and within KEEP_KM of it: {activity id: [(entry id, name of the race), ...]}. A race or a run whose position
    is not known counts as near (it cannot be told, and it is the day of a race). Such a run may well be the
    race (two runs that day and the other one was picked, no official time to tell them apart), so it is not
    dropped with the rest of a Garmin export; the runner pairs it by hand or deletes it."""
    races = con.execute(
        "SELECT e.id, ev.name, ev.date, ev.lat, ev.lon, ev.locations FROM entries e JOIN classes c ON c.id = e.class_id"
        " JOIN events ev ON ev.id = c.event_id WHERE e.user_id = ?", (user_id,)).fetchall()
    paired = {r[0] for r in con.execute("SELECT activity_id FROM entries WHERE user_id = ? AND activity_id IS NOT NULL",
                                        (user_id,))}
    out = {}
    for a in _activities(con, user_id):
        if a["id"] in paired:
            continue
        day = garmin.local(a["start"]).date().isoformat()
        for r in races:
            far = garmin.km_from(a, places(r)) if r["date"] == day else None
            if r["date"] == day and (far is None or far <= KEEP_KM):
                out.setdefault(a["id"], []).append((r["id"], r["name"]))
    return out


def ready(con, entry_id):
    """What the entry has: (activity, map with course, map without course)."""
    r = con.execute(
        "SELECT e.activity_id, c.course_file, ev.maponly_file FROM entries e JOIN classes c ON c.id = e.class_id"
        " JOIN events ev ON ev.id = c.event_id WHERE e.id = ?", (entry_id,)).fetchone()
    return bool(r and r["activity_id"]), bool(r and r["course_file"]), bool(r and r["maponly_file"])


def queue_analysis(con, entry_id, refit=True):
    """Queue the analysis when the entry has an activity and the map with the course."""
    has_act, has_course, _ = ready(con, entry_id)
    if not (has_act and has_course):
        return None
    user_id = con.execute("SELECT user_id FROM entries WHERE id = ?", (entry_id,)).fetchone()["user_id"]
    return jobs.enqueue(con, "analyse", user_id=user_id, entry_id=entry_id, payload=dict(refit=refit))
