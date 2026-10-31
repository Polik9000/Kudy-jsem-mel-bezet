"""Crossings that are not allowed at an event: lines drawn by hand (table `barriers`) and railways, motorways
and fences from OpenStreetMap (cached per event in the instance folder by the worker, see oroute/osm.py).
Both are shared by everyone who ran the event. Areas that must not be entered are read from the purple
hatching of the map with the course (oroute/hatch.py), so they are kept per class, like that map.
bestroute.py gets all of it as one JSON file (--barriers).

Whether the OpenStreetMap lines and the hatched areas are used is a setting of each runner (entries.own_*),
with the value of the race (events.osm_mode, hatch_mode) for those who did not choose: one runner's choice
never recalculates another runner's routes. A line drawn by hand is shared on purpose; it says who drew it
and only they may delete it."""
import json
import math
import os

from ..db import loads
from . import jobs

MODES = ("forbid", "penalty", "off")
HATCH_MODES = ("forbid", "off")


def _length_m(line):
    k = 111195.0
    return sum(math.hypot((b[0] - a[0]) * k, (b[1] - a[1]) * k * math.cos(math.radians(a[0])))
               for a, b in zip(line, line[1:]))


def manual(con, event_id, user_id=None):
    """The lines drawn by hand at the event. by: who drew it; mine: user_id may delete it (their own line, or
    one whose author's account is gone)."""
    out = []
    for r in con.execute("SELECT b.*, COALESCE(u.name, u.username) AS who FROM barriers b LEFT JOIN users u"
                         " ON u.id = b.created_by WHERE b.event_id = ? ORDER BY b.id", (event_id,)):
        line = loads(r["line"], [])
        out.append(dict(id=r["id"], kind=r["kind"], line=line, length_m=_length_m(line), by=r["who"],
                        mine=r["created_by"] in (None, user_id)))
    return out


def osm_path(conf, event_id):
    return conf.path("osm", f"event_{event_id}.json")


def osm_data(conf, event_id):
    """What was fetched from OpenStreetMap for the event (dict with lines, crossings, fetched) or None."""
    try:
        with open(osm_path(conf, event_id), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _osm_lines(conf, osm):
    """The OSM lines that are used: railways and motorways always, fences and walls only with OB_OSM_FENCES=1.
    Fences are off by default because nothing here shows they help: OpenStreetMap maps them unevenly (many
    around gardens, few in the forest) and a fence that is not there would send routes on detours."""
    return [l for l in osm.get("lines", []) if conf.osm_fences or l.get("what") != "fence"]


def for_map(con, conf, event_id, mode, user_id=None):
    """(manual lines, OSM lines and crossings or None) as the map page draws them for user_id."""
    osm = osm_data(conf, event_id) if mode != "off" else None
    if osm:
        osm = dict(lines=_osm_lines(conf, osm), crossings=osm.get("crossings", []))
    return [dict(id=b["id"], kind=b["kind"], line=b["line"], by=b["by"], mine=b["mine"])
            for b in manual(con, event_id, user_id)], osm


def hatch_path(conf, class_id):
    return conf.path("hatch", f"class_{class_id}.json")


def _stamp(course):
    """What tells one upload of the map with the course from the next."""
    st = os.stat(course)
    return [st.st_size, int(st.st_mtime)]


def hatch_data(conf, class_id, course=None):
    """What was read from the hatching of the class's map with the course (dict with areas, read) or None.
    With `course` (the path of that map) a reading of an older upload does not count."""
    try:
        with open(hatch_path(conf, class_id), encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    return None if course and d.get("source") != _stamp(course) else d


def save_hatch(conf, class_id, course, areas, read):
    os.makedirs(os.path.dirname(hatch_path(conf, class_id)), exist_ok=True)
    with open(hatch_path(conf, class_id), "w", encoding="utf-8") as f:
        json.dump(dict(areas=areas, source=_stamp(course), read=read), f)


def hatch_areas(conf, class_id, mode):
    """The out-of-bounds areas the map page draws and the routes keep out of: [[[lat, lon], ...], ...]."""
    d = hatch_data(conf, class_id) if mode != "off" else None
    return d["areas"] if d else []


def for_routing(con, conf, event_id, mode, areas=None):
    """The dict bestroute.py takes with --barriers, or None when there is nothing to forbid.
    OSM lines are 'forbidden' in mode forbid and 'hard' (very slow) in mode penalty; fences and walls from OSM
    (only with OB_OSM_FENCES=1) are always 'hard' (ISOM: impassable is not the same as forbidden).
    areas: the hatched out-of-bounds areas of the runner's map (hatch_areas)."""
    lines = [dict(kind=b["kind"], line=b["line"], source="manual") for b in manual(con, event_id)]
    crossings = []
    osm = osm_data(conf, event_id) if mode != "off" else None
    if osm:
        for l in _osm_lines(conf, osm):
            kind = "hard" if mode == "penalty" or l.get("kind") == "hard" else "forbidden"
            lines.append(dict(kind=kind, line=l["line"], source="osm", what=l.get("what")))
        crossings = osm.get("crossings", [])
    return dict(lines=lines, crossings=crossings, areas=areas or []) if lines or areas else None


def requeue_event(con, event_id, following=()):
    """The barriers changed: draw the best routes again for everyone at the event who has them.
    following: names of settings of the race that changed (osm_mode, hatch_mode); then only for the runners
    who follow the race in one of them, not for those with a setting of their own."""
    assert all(k in ("osm_mode", "hatch_mode") for k in following)
    own = " AND (" + " OR ".join(f"e.own_{k} IS NULL" for k in following) + ")" if following else ""
    n = 0
    for r in con.execute(
            "SELECT e.id, e.user_id FROM entries e JOIN classes c ON c.id = e.class_id JOIN analyses a ON a.entry_id = e.id"
            f" WHERE c.event_id = ? AND a.has_routes = 1{own}", (event_id,)).fetchall():
        n += requeue_entry(con, r["id"], r["user_id"])
    return n


def requeue_entry(con, entry_id, user_id):
    """Draw the best routes of one entry again (its track and splits stay as they are). Returns 1."""
    jobs.enqueue(con, "analyse", user_id=user_id, entry_id=entry_id, payload=dict(refit=False, routes_only=True))
    return 1


def save_osm(conf, event_id, data):
    path = osm_path(conf, event_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(f"{path}.{os.getpid()}.tmp", "w", encoding="utf-8") as f:      # whole or not at all
        json.dump(data, f, ensure_ascii=False)
    os.replace(f"{path}.{os.getpid()}.tmp", path)
